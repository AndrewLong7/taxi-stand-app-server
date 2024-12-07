from geopy.distance import geodesic
from enum import IntFlag
import time
import os
import sys
import json
import math
import googlemaps


# Define stand types using IntFlag
class TaxiStandType(IntFlag):
    URBAN = 1
    CROSS_HARBOUR = 2
    NT = 4
    LANTAU = 8


h3_distances = None


# 初始化 Google Maps 客户端
API_KEY = "AIzaSyDCVwtAq3cv1ZOvTM4pmSG1fvLLVYZ2Fj4"  # 替换为你的 API 密钥
gmaps = googlemaps.Client(key=API_KEY)


import osmnx as ox
import networkx as nx

road_network = None  # 设置全局的道路网络


def load_road_network(lat, lon, dist=3000):
    global road_network
    if road_network is None:
        road_network = ox.graph_from_point((lat, lon), dist=dist, network_type="drive")
    return road_network


import h3  # type: ignore


def calculate_h3_distance(user_lat, user_lng, stand_lat, stand_lng, h3_resolution=9):
    """
    使用 H3 网格系统计算两点之间的网格距离。

    Parameters:
    - user_lat, user_lng: 用户的纬度和经度。
    - stand_lat, stand_lng: 的士站点的纬度和经度。
    - h3_resolution: H3 网格分辨率（默认 9）。

    Returns:
    - 网格之间的距离（单位：跳数）。
    """
    user_h3 = h3.latlng_to_cell(user_lat, user_lng, h3_resolution)

    stand_h3 = h3.latlng_to_cell(stand_lat, stand_lng, h3_resolution)

    # 计算网格间的跳数
    h3_distance = h3.grid_distance(user_h3, stand_h3)
    return h3_distance


def calculate_osmnx_distance(lat1, lon1, lat2, lon2, fallback_distance=99999):
    global total_cal_dist_time  # Declare the use of the global variable
    try:
        G = load_road_network(lat1, lon1)

        orig_node = ox.distance.nearest_nodes(G, lon1, lat1)
        dest_node = ox.distance.nearest_nodes(G, lon2, lat2)

        # 检查路径是否存在
        if not nx.has_path(G, orig_node, dest_node):
            print("No path exists between the nodes. Returning fallback distance.")
            return fallback_distance

        length = nx.shortest_path_length(G, orig_node, dest_node, weight="length")
        return length / 1000  # 转换为公里

    except ValueError:
        print(
            f"Could not find a valid path, returning fallback distance of {fallback_distance} km"
        )
        return fallback_distance


import geopandas as gpd
from shapely.geometry import Point

# 定义区域划分规则
REGION_A = ["Central and Western", "Eastern", "Southern", "Wan Chai"]  # 区域A
REGION_B = []  # 其他区域归为区域B


def load_hk_geodata(geodata_path="geodata/hk.json"):
    """加载香港行政区地理数据"""
    return gpd.read_file(geodata_path)


def get_user_region(user_lat, user_lng, hk_geodata):
    """根据经纬度判断用户所在区域（区域A或区域B）"""
    user_location = Point(user_lng, user_lat)  # 经纬度顺序为 (lng, lat)
    for _, region in hk_geodata.iterrows():
        if region["geometry"].contains(user_location):
            if region["NAMEE"] in REGION_A:
                return "A"  # 属于区域A
            else:
                return "B"  # 属于区域B
    return None  # 如果找不到区域，返回 None


def filter_taxi_stands_by_region(user_region, stand_data):
    """根据用户所在区域筛选的士站点"""
    filtered_stands = []
    for stand in stand_data:
        # 根据站点所属区域进行筛选
        if (user_region == "A" and stand["region"] in REGION_A) or (
            user_region == "B" and stand["region"] not in REGION_A
        ):
            filtered_stands.append(stand)
    return filtered_stands


import pandas as pd
import numpy as np


def get_nearby_taxi_stands(
    user_lat, user_lng, user_hour, stand_type, stand_data, hk_geodata
):
    """结合用户区域仅搜索本区域内的站点"""
    # 确定用户所在区域
    user_region = get_user_region(user_lat, user_lng, hk_geodata)
    if not user_region:
        print("警告：用户位置不在已知区域内，无法推荐站点。")
        return []

    print(f"用户所在区域：{'区域A' if user_region == 'A' else '区域B'}")

    # 根据用户所在区域筛选站点
    filtered_stands = filter_taxi_stands_by_region(user_region, stand_data)

    # 转换站点列表为 pandas DataFrame
    df_stands = pd.DataFrame(filtered_stands)

    # 如果没有符合条件的站点，直接返回
    if df_stands.empty:
        print("没有符合条件的站点。")
        return []

    # 筛选符合用户站点类型的站点
    type_filter = (
        ((stand_type & TaxiStandType.URBAN) > 0) & df_stands["isUrban"]
        | ((stand_type & TaxiStandType.CROSS_HARBOUR) > 0) & df_stands["isCrossHarbour"]
        | ((stand_type & TaxiStandType.NT) > 0) & df_stands["isNTTaxi"]
        | ((stand_type & TaxiStandType.LANTAU) > 0) & df_stands["isLantauTaxi"]
    )

    df_stands = df_stands[type_filter]

    # 如果筛选后 DataFrame 为空，直接返回
    if df_stands.empty:
        print("筛选后没有符合条件的站点。")
        return []

    # 提取站点的纬度、经度
    stand_lats = df_stands["location"].apply(lambda loc: loc["lat"]).values
    stand_lngs = df_stands["location"].apply(lambda loc: loc["lng"]).values

    # 批量计算距离
    distances = calculate_distances_batch(user_lat, user_lng, stand_lats, stand_lngs)

    # 提取订单数量
    order_counts = (
        df_stands["order_count"]
        .apply(lambda orders: orders[str(user_hour).zfill(2)])
        .values
    )

    # 批量计算 f_score
    f_scores = calculate_f_scores_batch(distances, order_counts)

    # 将结果更新回 DataFrame
    df_stands["f_score"] = f_scores
    df_stands["order_count"] = order_counts
    df_stands["distance"] = distances
    # 按 f_score 排序，取前5个站点
    top_5_stands = df_stands.nlargest(5, "f_score")

    # 输出推荐结果
    print("\n按 f_score 推荐的前5个的士站点：")
    for i, row in top_5_stands.iterrows():
        print(
            f"站点 ID {row['stand_id']},距离: {row['distance']:.2f} km, "
            f"订单量: {row['order_count']},f_score: {row['f_score']:.2f}"
        )

    return top_5_stands["stand_id"].tolist()


def load_h3_distances(filename="h3_distances.json"):
    """Load the precomputed distances from a JSON file."""
    with open(filename, "r") as f:
        data = json.load(f)
    # Convert string keys back to tuples
    distances = {eval(key): value for key, value in data.items()}
    return distances


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


def get_resource_path(relative_path):
    """Get the absolute path to the resource, works for both development and PyInstaller environments."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# 从用户输入读取信息
def get_user_inputs():
    # 获取用户的经度和纬度
    user_lat = float(input("Please enter your latitude: "))
    user_lng = float(input("Please enter your longitude: "))

    # 获取用户的当前时间（小时）
    user_hour = int(input("Please enter the current hour (0-23): "))

    # 获取用户想要的站点类型
    print("Please select the taxi stand type(s):")
    print("1: Urban")
    print("2: Cross Harbour")
    print("4: New Territories")
    print("8: Lantau")
    print(
        "For multiple types, enter numbers separated by | (e.g., 1|2 for Urban and Cross Harbour)"
    )

    selected_types = input("Enter your selection: ")

    # 将输入的站点类型转换为 IntFlag
    stand_type = 0
    for part in selected_types.split("|"):
        stand_type |= int(part)

    return user_lat, user_lng, user_hour, stand_type


import copy


# ------------------------------------test_case-----------------------------------------------#
def main():
    print("Welcome to the Taxi Stand Finder!")
    # 加载香港行政区数据
    hk_geodata = load_hk_geodata()
    # 加载 JSON 数据
    json_file = get_resource_path("updated_taxi_stands.json")
    with open(json_file, "r", encoding="utf-8") as f:
        ori_stand_data = json.load(f)
    global h3_distances  # Declare the global variable
    h3_distances = load_h3_distances()
    # 允许用户多次查询
    while True:
        print("\n================ New Query =================")
        # 获取用户输入
        try:
            user_lat, user_lng, user_hour, stand_type = get_user_inputs()
        except ValueError:
            print("Invalid input. Please try again.")
            continue

        # 使用深拷贝的方式创建查询数据副本
        stand_data = copy.deepcopy(ori_stand_data)

        # 记录查询开始时间
        start_time = time.time()
        # 获取推荐的站点
        top_5_stand_ids = get_nearby_taxi_stands(
            user_lat, user_lng, user_hour, stand_type, stand_data, hk_geodata
        )

        # 记录查询结束时间
        end_time = time.time()

        print(
            "==============================================================================="
        )
        print(f"Query Time Total: {end_time - start_time:.4f} seconds")
        print(
            "==============================================================================="
        )
        print("Top 5 Stand IDs:", top_5_stand_ids)
        print(
            "==============================================================================="
        )

        # 提示用户是否继续查询
        continue_query = (
            input(
                "\nDo you want to perform another query? (yes to continue, 'exit' or 'quit' to terminate): "
            )
            .strip()
            .lower()
        )
        if continue_query in ["exit", "quit"]:
            print("Exiting the Taxi Stand Finder. Goodbye!")
            break


if __name__ == "__main__":
    main()
