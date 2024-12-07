import sys

from pydantic import BaseModel

sys.path.append(".")
from fastapi import FastAPI
from taxi_stands.type import TaxiStandType
from taxi_stands.utils import (
    get_nearby_taxi_stands,
    get_nearby_taxi_stands_v2,
    taxi_stand_data_pure,
    petrol_station_data,
)

app = FastAPI()


class NearbyTaxiStandsPayload(BaseModel):
    lat: float
    lng: float
    number: int
    coefficient: float
    stand_type: TaxiStandType


@app.post("/nearby_taxi_stands/")
async def read_nearby_taxi_stands(
    payload: NearbyTaxiStandsPayload,
):
    return get_nearby_taxi_stands_v2(
        payload.lat,
        payload.lng,
        payload.number,
        payload.coefficient,
        payload.stand_type,
    )


@app.get("/taxi_stands/")
async def all_taxi_stands():
    return taxi_stand_data_pure


@app.get("/petrol_stations/")
async def all_gas_stations():
    return petrol_station_data
