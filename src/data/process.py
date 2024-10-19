import json

f = open("./taxi_stands_data.json", "r", encoding="utf-8")
prefix = ["dummy", "HKI", "KLN", "NT"]
shift = 0
temp = 0
data = json.load(f)
for item in data:
    if item["stand_id"] == 1:
        shift += temp
        prefix.pop(0)
    temp = item["stand_id"]
    item["image_url"] = f"images/taxi_stands/{prefix[0]}{item['stand_id']}.png"
    item["stand_id"] += shift
    item["type"] = item["status"]
    del item["status"]


with open("./taxi_stands_data_new.json", "w", encoding="utf-8") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)
