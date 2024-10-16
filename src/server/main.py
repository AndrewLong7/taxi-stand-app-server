from fastapi import FastAPI
from taxi_stands.types import TaxiStandType
from taxi_stands.utils import get_nearby_taxi_stands, taxi_stand_data

app = FastAPI()


@app.post("/nearby_taxi_stands/")
async def read_nearby_taxi_stands(
    user_lat: float,
    user_lng: float,
    number: int = 5,
    coefficient: float = 0.5,
    stand_type: TaxiStandType = 15,
):
    return get_nearby_taxi_stands(user_lat, user_lng, number, coefficient, stand_type)


@app.get("/taxi_stands/")
async def all_taxi_stands():
    return taxi_stand_data

@app.get("/gas_stations/")
async def all_gas_stations():
    return taxi_stand_data
