"""Simulated sprinkler actuator"""

import time
import json

from config import (
    BROKER,
    PORT,
    SPRINKLER_TOKEN,
    TELEMETRY_TOPIC,
    ATTR_UPDATES_TOPIC,
    ATTR_REQUEST_TOPIC,
    ATTR_RESPONSE_TOPIC,
)

from utils import(
    create_mqtt_client,
    current_timestamp_ms,
    publish_telemetry,
    request_attributes,
    check_required_token,
)

SENSOR_LABEL = "SPRINKLER"

CHECK_INTERVAL = 1.0
DEFAULT_DURATION_SEC = 30.0

watering = False
watering_until_ms = 0
last_duration_sec = DEFAULT_DURATION_SEC

CSV_PATH = "data/raw/sprinkler.csv"
CSV_FIELDNAMES = ["timestamp_ms", "timestamp", "watering", "watering_until", "last_command"]
    
# Send current sprinkler state to ThingsBoard and CSV
def publish_state(client, last_command=""):
    values = {
        "watering": watering,
        "watering_until": watering_until_ms,
        "last_command": last_command
    }

    return publish_telemetry(client=client, telemetry_topic=TELEMETRY_TOPIC, values=values, label=SENSOR_LABEL, csv_path=CSV_PATH, csv_fieldnames=CSV_FIELDNAMES)

# Start watering for the configured duration
def start_watering(client, duration_sec, source="cmd"):
    global watering, watering_until_ms

    watering = True
    watering_until_ms = current_timestamp_ms() + int(float(duration_sec) * 1000)
    
    return publish_state(client=client, last_command=f"{source}:start({duration_sec}s)")

# Stop watering and clear the planned stop time
def stop_watering(client, source="cmd"):
    global watering, watering_until_ms

    watering = False
    watering_until_ms = 0

    return publish_state(client=client, last_command=f"{source}:stop")

# Apply watering and duration commands received from ThingsBoard
def apply_attr_command(client, attrs, source="shared"):
    global last_duration_sec

    # Update watering duration if a new value is received
    if "duration" in attrs:
        last_duration_sec = attrs["duration"]

    # If there is no watering command, only duration was updated
    if "watering" not in attrs:
        return
    
    desired_watering = attrs["watering"]

    # Ignore repeated command if the state did not change
    if desired_watering == watering:
        print(f"[{SENSOR_LABEL}] Same state ignored.")
        return
    
    if desired_watering:
        start_watering(client=client, duration_sec=last_duration_sec, source=source)
    else:
        stop_watering(client=client, source=source)

# Subscribe to attribute messages and request saved duration
def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_LABEL}] Connected with result code {rc}")

    if rc == 0:
        client.subscribe(ATTR_UPDATES_TOPIC)
        client.subscribe(ATTR_RESPONSE_TOPIC)

        publish_state(client, last_command="boot")

        request_attributes(client=client, attr_request_topic=ATTR_REQUEST_TOPIC, shared_keys="duration")

# Read attribute messages from ThingsBoard
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"[{SENSOR_LABEL}] Received attribute message: {payload}")

    try:
        data = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        print(f"[{SENSOR_LABEL}] Non-JSON payload:", payload)
        return
    
    if msg.topic == ATTR_UPDATES_TOPIC:
        apply_attr_command(client=client, attrs=data, source="attrUpdate")
        return

    if msg.topic.startswith("v1/devices/me/attributes/response/"):
        shared_attrs = data.get("shared")

        if "duration" in shared_attrs:
            apply_attr_command(client=client, attrs={"duration": shared_attrs["duration"]}, source="attrResponse")

def main():
    access_token = check_required_token(SPRINKLER_TOKEN, "SPRINKLER_TOKEN")

    client = create_mqtt_client(access_token=access_token, on_connect=on_connect, on_message=on_message)

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            now = current_timestamp_ms()

            # Stop watering automatically when planned stop time is reached
            if watering and watering_until_ms > 0 and now >= watering_until_ms:
                result = stop_watering(client, source="autoStop")
                result.wait_for_publish()

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"Stopping {SENSOR_LABEL}...")

        if watering:
            result = stop_watering(client=client, source="shutdown")
        else:
            result = publish_state(client=client, last_command="shutdown")

        result.wait_for_publish()

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()