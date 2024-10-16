from geopy.distance import geodesic
from enum import IntFlag
from types import TaxiStandType
import json
from typing import List


taxi_stand_data_url = "../data/taxi_stands_demand_client.json"

with open(taxi_stand_data_url, "r") as f:
    taxi_stand_data = json.load(f)



def haversine_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


def calculate_f_score(distance, order_count, alpha=1, beta=1):
    return alpha / distance + beta * order_count


def get_nearby_taxi_stands(
    user_lat: float,
    user_lng: float,
    number: int,
    coefficient: float,
    stand_type: TaxiStandType,
):
    candidates = []

    for stand in taxi_stand_data:
        if (
            (stand_type & TaxiStandType.URBAN and stand["isUrban"])
            or (stand_type & TaxiStandType.CROSS_HARBOUR and stand["isCrossHarbour"])
            or (stand_type & TaxiStandType.NT and stand["isNTTaxi"])
            or (stand_type & TaxiStandType.LANTAU and stand["isLantauTaxi"])
        ):
            stand_lat = stand["location"]["lat"]
            stand_lng = stand["location"]["lng"]
            distance = haversine_distance(user_lat, user_lng, stand_lat, stand_lng)
            order_count = sum(stand["order_count"].values())
            f_score = calculate_f_score(
                distance, order_count, alpha=coefficient, beta=1 - coefficient
            )
            stand["f_score"] = f_score
            candidates.append(stand)

    sorted_candidates = sorted(candidates, key=lambda x: x["f_score"], reverse=True)
    return sorted_candidates[:number]
