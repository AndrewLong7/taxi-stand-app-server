import json
import geopandas as gpd
from shapely.geometry import Point

REGION_A = ["Central and Western", "Eastern", "Southern", "Wan Chai"]


def taxi_stands():
    f = open("./taxi_stands_data.json", "r", encoding="utf-8")
    data = json.load(f)
    for item in data:
        del item["order_count"]

    with open("./taxi_stands_data_pure.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


def get_user_region(user_lat, user_lng, hk_geodata):
    """根据经纬度判断用户所在区域（区域A或区域B）"""
    user_location = Point(user_lng, user_lat)  # 经纬度顺序为 (lng, lat)
    for _, region in hk_geodata.iterrows():
        if region["geometry"].contains(user_location):
            return region["NAMEE"]
    raise ValueError("User location not in HK")


def adding_region():

    hk_boundary = gpd.read_file("./hk_boundary.json")

    count = 0
    regions = set()

    with open("./taxi_stands_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        try:
            region = get_user_region(
                item["location"]["latitude"], item["location"]["longitude"], hk_boundary
            )
            regions.add(region)
        except Exception as e:
            count += 1
            print(f"{count}----")
            print(e)
            print(item)
            continue

    print(f"\n{count}/{len(data)}", len(regions))


if __name__ == "__main__":
    adding_region()
