"""Simulated soil moisture sensor"""

import time
import json
import random

from config import (
    BROKER,
    PORT,
    SOIL_MOISTURE_SENSOR_TOKEN,
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
    publish_attributes,
    request_attributes,
    check_required_token,
    wait_for,
)

SENSOR_LABEL = "SOIL MOISTURE SENSOR"

SEND_INTERVAL = 1.0  
STATE_SAVE_INTERVAL = 5.0

SOIL_MOISTURE_MIN = 0.0       
SOIL_MOISTURE_MAX = 100.0      
INITIAL_SOIL_MOISTURE = 41.0

BASE_DRY_RATE = 0.035 
TEMP_DRY_FACTOR = 0.008
AIR_HUMIDITY_DRY_FACTOR = 0.003 
FLOW_MOISTURE_FACTOR = 0.11
NOISE = 0.04

STATE_ATTRIBUTE = "last_soil_moisture"

sprinkler_on = False
current_temperature = 24.0
current_air_humidity = 60.0
current_water_flow = 0.0

soil_moisture = INITIAL_SOIL_MOISTURE
state_initialized = False

CSV_PATH = "data/raw/soil_moisture_sensor.csv"
CSV_FIELDNAMES = ["timestamp_ms", "timestamp", "soil_moisture", "sensor_alive"]

# Subscribe to attribute updates and request the latest soil moisture
def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_LABEL}] Connected with result code {rc}")

    if rc == 0:
        client.subscribe(ATTR_UPDATES_TOPIC)
        client.subscribe(ATTR_RESPONSE_TOPIC)

        request_attributes(client=client, attr_request_topic=ATTR_REQUEST_TOPIC, client_keys=STATE_ATTRIBUTE,
                           shared_keys="sprinkler_on,current_temperature,current_air_humidity,current_water_flow")

# Read saved soil moisture and latest shared sensor values
def on_message(client, userdata, msg):
    global sprinkler_on, current_temperature, current_air_humidity, current_water_flow
    global soil_moisture, state_initialized

    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[ATTR] Non-JSON payload: {msg.payload}")
        return
    
    attrs = extract_attributes(data)

    if STATE_ATTRIBUTE in attrs and not state_initialized:
        soil_moisture = attrs[STATE_ATTRIBUTE]
        state_initialized = True
        print(f"[{SENSOR_LABEL}] restored {STATE_ATTRIBUTE} -> {soil_moisture}")

    if "sprinkler_on" in attrs:
        new_sprinkler_state = attrs["sprinkler_on"]

        if new_sprinkler_state != sprinkler_on:
            sprinkler_on = new_sprinkler_state
            print(f"[{SENSOR_LABEL}] sprinkler_on -> {sprinkler_on}")

        if not sprinkler_on:
            current_water_flow = 0.0

    if "current_temperature" in attrs:
        current_temperature = attrs["current_temperature"]

    if "current_air_humidity" in attrs:
        current_air_humidity = attrs["current_air_humidity"]

    if "current_water_flow" in attrs:
        current_water_flow = attrs["current_water_flow"]
        if not sprinkler_on:
            current_water_flow = 0.0

# Use saved soil moisture if available; otherwise use the configured default
def wait_for_initial_state():
    global state_initialized

    if not wait_for(lambda: state_initialized, timeout_sec=3.0):
        print(f"[{SENSOR_LABEL}] no saved {STATE_ATTRIBUTE} found, using default -> {soil_moisture}")
        state_initialized = True

# Calculate the next soil moisture value with temperature, air humidity and water flow effect
def update_soil_moisture(current_value):
    temperature_effect = max(0.0, current_temperature - 24.0) * TEMP_DRY_FACTOR
    air_humidity_effect = max(0.0, 60.0 - current_air_humidity) * AIR_HUMIDITY_DRY_FACTOR

    drying_rate = BASE_DRY_RATE + temperature_effect + air_humidity_effect

    if sprinkler_on:
        watering_effect = current_water_flow * FLOW_MOISTURE_FACTOR
        moisture_change = watering_effect - drying_rate
    else:
        moisture_change = -drying_rate

    moisture_change += random.uniform(-NOISE, NOISE)

    return limit_to_range(current_value + moisture_change, SOIL_MOISTURE_MIN, SOIL_MOISTURE_MAX)

# Save current soil moisture to ThingsBoard
def save_state(client):
    return publish_attributes(client=client, attr_topic=ATTR_UPDATES_TOPIC, values={STATE_ATTRIBUTE: round(soil_moisture, 2)}, label=SENSOR_LABEL)

def main():
    global soil_moisture
    
    access_token = check_required_token(SOIL_MOISTURE_SENSOR_TOKEN, "SOIL_MOISTURE_SENSOR_TOKEN")

    client = create_mqtt_client(access_token=access_token, on_connect=on_connect, on_message=on_message)

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    wait_for_initial_state()

    last_state_save_time = 0.0

    try:
        while True:
            soil_moisture = update_soil_moisture(soil_moisture)

            values = {
                "soil_moisture": round(soil_moisture, 2),
                "sensor_alive": 1
            }

            publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

            now = time.time()

            if now - last_state_save_time >= STATE_SAVE_INTERVAL:
                save_state(client)
                last_state_save_time = now

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print(f"Stopping {SENSOR_LABEL}...")

        state_result = save_state(client)

        values = {
            "sensor_alive": 0,
        }

        result = publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

        state_result.wait_for_publish()
        result.wait_for_publish()

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()