from geopy.distance import geodesic
from enum import IntFlag
import json


# 定义站点类型的 IntFlag
class TaxiStandType(IntFlag):
    URBAN = 1
    CROSS_HARBOUR = 1 << 1
    NT = 1 << 2
    LANTAU = 1 << 3


def haversine_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


def calculate_f_score(distance, order_count, alpha=1, beta=1):
    return alpha / distance + beta * order_count


def get_nearby_taxi_stands(user_lat, user_lng, user_hour, stand_type, stand_data):
    candidates = []

    for stand in stand_data:
        if (
            (stand_type & TaxiStandType.URBAN and stand["isUrban"])
            or (stand_type & TaxiStandType.CROSS_HARBOUR and stand["isCrossHarbour"])
            or (stand_type & TaxiStandType.NT and stand["isNTTaxi"])
            or (stand_type & TaxiStandType.LANTAU and stand["isLantauTaxi"])
        ):

            stand_lat = stand["location"]["lat"]
            stand_lng = stand["location"]["lng"]
            distance = haversine_distance(user_lat, user_lng, stand_lat, stand_lng)

            order_count = stand["order_count"][str(user_hour).zfill(2)]

            f_score = calculate_f_score(distance, order_count)
            stand["f_score"] = f_score

            candidates.append(stand)

    top_5_stand_ids = [
        stand["stand_id"]
        for stand in sorted(candidates, key=lambda x: x["f_score"], reverse=True)[:5]
    ]
    return top_5_stand_ids


user_lat = 22.3226243
user_lng = 114.2089527
user_hour = 5
stand_type = (
    TaxiStandType.URBAN | TaxiStandType.CROSS_HARBOUR
)  # 想要获取城市和过海的士站


with open(
    "../data/taxi_stands_demand_client.json",
    "r",
) as f:
    stand_data = json.load(f)

# get_top5:
top_5_stand_ids = get_nearby_taxi_stands(
    user_lat, user_lng, user_hour, stand_type, stand_data
)
print(top_5_stand_ids)
