"""Simulate temperature sensor"""

import time
import random
import math
import json

from config import (
    BROKER,
    PORT,
    TEMPERATURE_SENSOR_TOKEN,
    TELEMETRY_TOPIC,
    ATTR_UPDATES_TOPIC,
    ATTR_REQUEST_TOPIC,
    ATTR_RESPONSE_TOPIC,
)

from utils import (
    limit_to_range,
    create_mqtt_client,
    extract_attributes,
    publish_telemetry,
    publish_attributes,
    request_attributes,
    check_required_token,
    wait_for,
)

SENSOR_LABEL = "TEMPERATURE SENSOR"

SEND_INTERVAL = 1.0
STATE_SAVE_INTERVAL = 5.0
CYCLE_SECONDS = 300

TEMP_MIN = 10.0
TEMP_MAX = 40.0
BASE_TEMPERATURE = 24.0
TEMPERATURE_AMPLITUDE = 4.0
NOISE = 0.25

STATE_ATTRIBUTE = "temperature_cycle_time_sec"

temperature_cycle_time_sec = 0.0
temperature_cycle_time_ready = False

CSV_PATH = "data/raw/temperature_sensor.csv"
CSV_FIELDNAMES = ["timestamp_ms", "timestamp", "temperature", "sensor_alive"]

# Generate temperature that changes smoothly over time (with small random noise)
def generate_temperature(temperature_cycle_time_sec):
    cycle_position = (temperature_cycle_time_sec % CYCLE_SECONDS) / CYCLE_SECONDS

    temperature = BASE_TEMPERATURE + TEMPERATURE_AMPLITUDE * math.sin(2 * math.pi * cycle_position)
    temperature += random.uniform(-NOISE, NOISE)

    return limit_to_range(temperature, TEMP_MIN, TEMP_MAX)

# After connection, request saved cycle time from ThingsBoard
def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_LABEL}] Connected with result code {rc}")

    if rc == 0:
        client.subscribe(ATTR_RESPONSE_TOPIC)

        request_attributes(client=client, attr_request_topic=ATTR_REQUEST_TOPIC, client_keys=STATE_ATTRIBUTE)
    
# Read saved cycle time from ThingsBoard response
def on_message(client, userdata, msg):
    global temperature_cycle_time_sec, temperature_cycle_time_ready

    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[ATTR] Non-JSON payload: {msg.payload}")
        return
    
    attrs = extract_attributes(data)
    
    if STATE_ATTRIBUTE in attrs and not temperature_cycle_time_ready:
        temperature_cycle_time_sec = attrs[STATE_ATTRIBUTE]
        temperature_cycle_time_ready = True
        print(f"[{SENSOR_LABEL}] restored {STATE_ATTRIBUTE} -> {temperature_cycle_time_sec}")

# Use saved cycle state if it exists; otherwise start from the beginning
def wait_for_initial_state():
    global temperature_cycle_time_ready

    if not wait_for(lambda: temperature_cycle_time_ready, timeout_sec=3.0):
        print(f"[{SENSOR_LABEL}] no saved {STATE_ATTRIBUTE} found, using default -> {temperature_cycle_time_sec}")
        temperature_cycle_time_ready = True

# Save current cycle time to ThingsBoard
def save_state(client):
    return publish_attributes(client=client, attr_topic=ATTR_UPDATES_TOPIC, values={STATE_ATTRIBUTE: round(temperature_cycle_time_sec, 2)},label=SENSOR_LABEL)

def main():
    global temperature_cycle_time_sec

    access_token = check_required_token(TEMPERATURE_SENSOR_TOKEN, "TEMPERATURE_SENSOR_TOKEN")

    client = create_mqtt_client(access_token=access_token, on_connect=on_connect, on_message=on_message)

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    wait_for_initial_state()

    last_state_save_time = 0

    try:
        while True:
            temperature = generate_temperature(temperature_cycle_time_sec)

            values = {
                "temperature": round(temperature, 2),
                "sensor_alive": 1
            }

            publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

            temperature_cycle_time_sec = (temperature_cycle_time_sec + SEND_INTERVAL) % CYCLE_SECONDS

            now = time.time()

            if now - last_state_save_time >= STATE_SAVE_INTERVAL:
                save_state(client)
                last_state_save_time = now

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print(f"Stopping {SENSOR_LABEL}...")

        attr_result = save_state(client)

        values = {
            "sensor_alive": 0,
        }

        result = publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

        attr_result.wait_for_publish()
        result.wait_for_publish()

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()