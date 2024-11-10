import time
from geopy.distance import geodesic
from taxi_stands.type import TaxiStandType
import json
from typing import List

taxi_stand_data_pure_url = "./data/taxi_stands_data_pure.json"
taxi_stand_data_url = "./data/taxi_stands_data.json"
petrol_station_data_url = "./data/petrol_stations.json"

with open(taxi_stand_data_pure_url, "r") as f:
    taxi_stand_data_pure = json.load(f)

with open(taxi_stand_data_url, "r") as f:
    taxi_stand_data = json.load(f)

with open(petrol_station_data_url, "r") as f:
    petrol_station_data = json.load(f)


def haversine_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


def calculate_f_score(
    distance, order_count, alpha=5, beta=0.5, lambda_l1=0.1, lambda_l2=0.1
):
    """Calculate the f_score using adjusted parameters for distance and order_count"""

    # L1 正则化项（绝对值）
    l1_regularization = lambda_l1 * (abs(distance) + abs(order_count))

    # L2 正则化项（平方）
    l2_regularization = lambda_l2 * (distance**2 + order_count)
    # f_score 计算，调整 alpha 和 beta，减弱正则化项
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
            order_count = stand["order_count"][str(user_hour).zfill(2)]
            f_score = calculate_f_score(distance, order_count)
            stand["f_score"] = f_score
            candidates.append(stand)

    sorted_candidates = sorted(candidates, key=lambda x: x["f_score"], reverse=True)[
        :number
    ]

    return sorted_candidates
