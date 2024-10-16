from fastapi import FastAPI
from geopy.distance import geodesic
from enum import IntFlag
import json
from typing import List
from pydantic import BaseModel

app = FastAPI()

# Load data once
with open("../data/taxi_stands_demand_client.json", "r") as f:
    stand_data = json.load(f)


class TaxiStandType(IntFlag):
    URBAN = 1
    CROSS_HARBOUR = 1 << 1
    NT = 1 << 2
    LANTAU = 1 << 3


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
            order_count = sum(stand["order_count"].values())
            f_score = calculate_f_score(
                distance, order_count, alpha=coefficient, beta=1 - coefficient
            )
            stand["f_score"] = f_score
            candidates.append(stand)

    sorted_candidates = sorted(candidates, key=lambda x: x["f_score"], reverse=True)
    return sorted_candidates[:number]


@app.get("/get_nearby_taxi_stands/")
async def read_nearby_taxi_stands(
    user_lat: float,
    user_lng: float,
    number: int = 5,
    coefficient: float = 0.5,
    stand_type: TaxiStandType = 15,
):
    return get_nearby_taxi_stands(user_lat, user_lng, number, coefficient, stand_type)


@app.get("/get_all_data/")
async def read_all_data():
    return stand_data
