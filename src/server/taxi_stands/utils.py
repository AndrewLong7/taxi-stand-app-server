import time
from geopy.distance import geodesic
from taxi_stands.type import TaxiStandType, RecommandationType
import json
import geopandas as gpd
import copy
from shapely.geometry import Point
import pandas as pd
import numpy as np
import googlemaps
import h3

REGION_A = ["Central and Western", "Eastern", "Southern", "Wan Chai"]
REGION_B = []

h3_distances = None

API_KEY = "AIzaSyDCVwtAq3cv1ZOvTM4pmSG1fvLLVYZ2Fj4"
gmaps = googlemaps.Client(key=API_KEY)

taxi_stand_data_pure_url = "./data/taxi_stands_data_pure.json"
taxi_stand_data_url = "./data/taxi_stands_data.json"
petrol_station_data_url = "./data/petrol_stations.json"
hk_boundary_url = "./data/hk_boundary.json"


def load_h3_distances(filename="./data/h3_distances.json"):
    with open(filename, "r") as f:
        data = json.load(f)
    distances = {eval(key): value for key, value in data.items()}
    return distances


h3_distance = load_h3_distances()


with open(taxi_stand_data_pure_url, "r") as f:
    taxi_stand_data_pure = json.load(f)

with open(taxi_stand_data_url, "r") as f:
    taxi_stand_data = json.load(f)

with open(petrol_station_data_url, "r") as f:
    petrol_station_data = json.load(f)

hk_boundary = gpd.read_file(hk_boundary_url)


def haversine_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


def calculate_f_score(
    distance, order_count, alpha=5, beta=0.5, lambda_l1=0.1, lambda_l2=0.1
):
    """Calculate the f_score using adjusted parameters for distance and order_count"""

    l1_regularization = lambda_l1 * (abs(distance) + abs(order_count))

    l2_regularization = lambda_l2 * (distance**2 + order_count)
    f_score = (alpha / distance) + (beta * order_count) - l2_regularization

    return f_score


def get_nearby_taxi_stands(
    user_lat: float,
    user_lng: float,
    number: int,
    coefficient: float,
    stand_type: TaxiStandType,
):
    candidates = []
    user_hour = time.localtime().tm_hour

    for stand in taxi_stand_data:
        if (
            (stand_type & TaxiStandType.URBAN and stand["isUrban"])
            or (stand_type & TaxiStandType.CROSS_HARBOUR and stand["isCrossHarbour"])
            or (stand_type & TaxiStandType.NT and stand["isNTTaxi"])
            or (stand_type & TaxiStandType.LANTAU and stand["isLantauTaxi"])
        ):
            stand_lat = stand["location"]["latitude"]
            stand_lng = stand["location"]["longitude"]
            distance = haversine_distance(user_lat, user_lng, stand_lat, stand_lng)
            stand["distance"] = distance
            try:
                order_count = stand["order_count"][str(user_hour).zfill(2)]
                stand["order_count"] = int(order_count)
            except Exception as e:
                order_count = 0
                stand["order_count"] = order_count
            f_score = calculate_f_score(distance, order_count)
            stand["f_score"] = f_score
            candidates.append(stand)

    if coefficient == 1:  # nearest
        sorted_candidates = sorted(candidates, key=lambda x: x["distance"])[:number]
    elif coefficient == 2:  # most ordered
        sorted_candidates = sorted(
            candidates, key=lambda x: x["order_count"], reverse=True
        )[:number]
    else:  # recommended
        sorted_candidates = sorted(
            candidates, key=lambda x: x["f_score"], reverse=True
        )[:number]

    return sorted_candidates


def get_user_region(user_lat, user_lng, hk_geodata):
    user_location = Point(user_lng, user_lat)  # 经纬度顺序为 (lng, lat)
    for _, region in hk_geodata.iterrows():
        if region["geometry"].contains(user_location):
            if region["NAMEE"] in REGION_A:
                return "A"  # 属于区域A
            else:
                return "B"  # 属于区域B
    return None  # 如果找不到区域，返回 None


def filter_taxi_stands_by_region(user_region, stand_data):
    filtered_stands = []
    for stand in stand_data:
        if (user_region == "A" and stand["region"] in REGION_A) or (
            user_region == "B" and stand["region"] not in REGION_A
        ):
            filtered_stands.append(stand)
    return filtered_stands


def calculate_distances_batch(
    user_lat, user_lng, stand_lats, stand_lngs, batch_size=25, h3_resolution=9
):
    """
    Calculate distances using Google Maps and fallback to H3 precomputed distances.
    """
    global h3_distances  # Use the global variable

    if h3_distances is None:
        raise ValueError(
            "H3 distances are not loaded. Please ensure they are initialized."
        )

    distances = []
    origins = [(user_lat, user_lng)]
    destinations = list(zip(stand_lats, stand_lngs))
    for i in range(0, len(destinations), batch_size):
        batch_destinations = destinations[i : i + batch_size]
        try:
            results = gmaps.distance_matrix(origins, batch_destinations, mode="driving")
            batch_distances = []
            for idx, elem in enumerate(results["rows"][0]["elements"]):
                if "distance" in elem and elem["status"] == "OK":
                    batch_distances.append(elem["distance"]["value"] / 1000)
                else:
                    print("path does not exit in googlemap")
                    # Fallback to H3 distance
                    stand_lat, stand_lng = batch_destinations[idx]
                    user_h3 = h3.latlng_to_cell(user_lat, user_lng, h3_resolution)
                    stand_h3 = h3.latlng_to_cell(stand_lat, stand_lng, h3_resolution)
                    batch_distances.append(
                        h3_distances.get((user_h3, stand_h3), float("inf"))
                    )
            distances.extend(batch_distances)
        except Exception as e:
            print(f"Google Maps API Error in batch {i // batch_size + 1}: {e}")
            distances.extend([float("inf")] * len(batch_destinations))
    return np.array(distances)


def calculate_f_scores_batch(
    distances, order_counts, max_distance=50, max_order=50, alpha=4, beta=0.5, gamma=0.3
):
    """
    优化后的批量计算 f_score。
    """
    # 矢量化归一化
    normalized_distances = np.minimum(distances / max_distance, 1)
    normalized_order_counts = np.minimum(order_counts / max_order, 1)

    # 矢量化计算
    distance_effect = alpha * np.exp(-gamma * normalized_distances)
    order_effect = beta * normalized_order_counts

    # 直接返回 f_score
    return distance_effect + order_effect


def _get_nearby_taxi_stands(
    user_lat,
    user_lng,
    user_hour,
    stand_type,
    stand_data,
    recommend_type=RecommandationType.RECOMMENDED,
    number=5,
):
    """结合用户区域仅搜索本区域内的站点"""
    hk_geodata = hk_boundary
    user_region = get_user_region(user_lat, user_lng, hk_geodata)
    if not user_region:
        raise ValueError("user location is not in HK")

    filtered_stands = filter_taxi_stands_by_region(user_region, stand_data)
    df_stands = pd.DataFrame(filtered_stands)

    if df_stands.empty:
        raise ValueError("No taxi stands in user region")

    type_filter = (
        ((stand_type & TaxiStandType.URBAN) > 0) & df_stands["isUrban"]
        | ((stand_type & TaxiStandType.CROSS_HARBOUR) > 0) & df_stands["isCrossHarbour"]
        | ((stand_type & TaxiStandType.NT) > 0) & df_stands["isNTTaxi"]
        | ((stand_type & TaxiStandType.LANTAU) > 0) & df_stands["isLantauTaxi"]
    )

    df_stands = df_stands[type_filter]

    if df_stands.empty:
        raise ValueError("No taxi stands in user region")

    stand_lats = df_stands["location"].apply(lambda loc: loc["lat"]).values
    stand_lngs = df_stands["location"].apply(lambda loc: loc["lng"]).values

    distances = calculate_distances_batch(user_lat, user_lng, stand_lats, stand_lngs)

    order_counts = (
        df_stands["order_count"]
        .apply(lambda orders: orders[str(user_hour).zfill(2)])
        .values
    )

    f_scores = calculate_f_scores_batch(distances, order_counts)

    df_stands["f_score"] = f_scores
    df_stands["order_count"] = order_counts
    df_stands["distance"] = distances
    if recommend_type == RecommandationType.RECOMMENDED:
        candidates = df_stands.nlargest(number, "f_score")
    elif recommend_type == RecommandationType.DISTANCE:
        candidates = df_stands.nsmallest(number, "distance")
    else:
        candidates = df_stands.nlargest(number, "order_count")

    return candidates["stand_id"].tolist()


def get_nearby_taxi_stands_v2(
    user_lat: float,
    user_lng: float,
    number: int,
    recommend_type: RecommandationType,
    stand_type: TaxiStandType,
):
    candidates = []

    user_hour = str(time.localtime().tm_hour).zfill(2)
    stand_data = copy.deepcopy(taxi_stand_data)

    candidates = _get_nearby_taxi_stands(
        user_lat, user_lng, user_hour, stand_type, stand_data, recommend_type, number
    )

    return candidates
