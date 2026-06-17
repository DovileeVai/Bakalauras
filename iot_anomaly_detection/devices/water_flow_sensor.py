"""Simulated water flow sensor"""

import time
import json
import random

from config import (
    BROKER,
    PORT,
    WATER_FLOW_SENSOR_TOKEN,
    TELEMETRY_TOPIC,
    ATTR_UPDATES_TOPIC,
    ATTR_REQUEST_TOPIC,
    ATTR_RESPONSE_TOPIC,
)

from utils import(
    limit_to_range,
    create_mqtt_client,
    extract_attributes,
    publish_telemetry,
    request_attributes,
    check_required_token,
)

SENSOR_LABEL = "WATER FLOW SENSOR"

SEND_INTERVAL = 1.0

FLOW_MIN = 0.0
FLOW_MAX = 5.0
NORMAL_FLOW_MIN = 1.5
NORMAL_FLOW_MAX = 2.5
NOISE = 0.08

sprinkler_on = False

CSV_PATH = "data/raw/water_flow_sensor.csv"
CSV_FIELDNAMES = ["timestamp_ms", "timestamp", "water_flow", "sensor_alive"]

# Request current sprinkler state after connection
def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_LABEL}] Connected with result code {rc}")

    if rc == 0:
        client.subscribe(ATTR_UPDATES_TOPIC)
        client.subscribe(ATTR_RESPONSE_TOPIC)

        request_attributes(client=client, attr_request_topic=ATTR_REQUEST_TOPIC, shared_keys="sprinkler_on")

# Update sprinkler state when an attribute message is received
def on_message(client, userdata, msg):
    global sprinkler_on

    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print("[ATTR] Non-JSON payload:", msg.payload)
        return
    
    attrs = extract_attributes(data)

    if "sprinkler_on" in attrs:
        new_value = attrs["sprinkler_on"]

        if new_value != sprinkler_on:
            sprinkler_on = new_value
            print(f"[{SENSOR_LABEL}] sprinkler_on changed -> {sprinkler_on}")

# Generate water flow according to the sprinkler state
def generate_water_flow():
    if sprinkler_on:
        water_flow = random.uniform(NORMAL_FLOW_MIN, NORMAL_FLOW_MAX)
        water_flow += random.uniform(-NOISE, NOISE)
    else:
        water_flow = 0.0
    
    return limit_to_range(water_flow, FLOW_MIN, FLOW_MAX)

def main():
    access_token = check_required_token(WATER_FLOW_SENSOR_TOKEN, "WATER_FLOW_SENSOR_TOKEN")

    client = create_mqtt_client(access_token=access_token, on_connect=on_connect, on_message=on_message)

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            water_flow = generate_water_flow()

            values = {
                "water_flow": round(water_flow, 2),
                "sensor_alive": 1
            }

            publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print(f"Stopping {SENSOR_LABEL}...")

        values = {
                "sensor_alive": 0,
            }

        result = publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

        result.wait_for_publish()

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()        