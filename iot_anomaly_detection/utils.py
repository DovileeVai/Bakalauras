import json
import time
import paho.mqtt.client as mqtt

from datetime import datetime

import csv
from pathlib import Path

# Limit value to the provided interval
def limit_to_range(value, minimum, maximum):
    return max(minimum, min(maximum, value))

# Form a readable timestamp: YYYY-MM-DD HH:MM:SS
def form_timestamp(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

# Return the current timestamp in milliseconds
def current_timestamp_ms():
    return int(time.time() * 1000)

# Check whether a device access token is configured
def check_required_token(value, env_name):
    if not value:
        raise RuntimeError(f"{env_name} is missing. Check the .env file.")
    return value

# Create an MQTT client authenticated with a ThingsBoard access token
def create_mqtt_client(access_token, on_connect=None, on_message=None):
    client = mqtt.Client()
    client.username_pw_set(access_token)

    if on_connect is not None:
        client.on_connect = on_connect

    if on_message is not None:
        client.on_message = on_message

    return client

# Save one telemetry row to a CSV file
def save_row_to_csv(csv_path, row, fieldnames):
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        writer.writerow(row)

# Publish telemetry values using ThingsBoard time-series payload format
def publish_telemetry(client, telemetry_topic, values, label, csv_path=None, csv_fieldnames=None):
    timestamp_ms = current_timestamp_ms()

    payload = {
        "ts": timestamp_ms,
        "values": values
    }

    result = client.publish(telemetry_topic, json.dumps(payload), qos=1)

    readable_time = form_timestamp(timestamp_ms)
    print(f"[{label}] {readable_time} Sending:", payload)

    if csv_path is not None:
        row = {
            "timestamp_ms": timestamp_ms,
            "timestamp": readable_time,
            **values
        }

        save_row_to_csv(csv_path, row, csv_fieldnames)

    return result

# Publish client-side attributes to ThingsBoard
def publish_attributes(client, attr_topic, values, label):
    result = client.publish(attr_topic, json.dumps(values), qos=1)
    print(f"[{label}] Sent attributes:", values)
    return result

# Request client-side and/or shared attributes from ThingsBoard
def request_attributes(client, attr_request_topic, client_keys="", shared_keys=""):
    request_id = current_timestamp_ms() % 100000
    topic = attr_request_topic.format(request_id)

    payload = {}

    if client_keys:
        payload["clientKeys"] = client_keys

    if shared_keys:
        payload["sharedKeys"] = shared_keys

    result = client.publish(topic, json.dumps(payload), qos=1)
    print(f"[ATTR] Requested attrs: {payload}")

    return result

# Normalize ThingsBoard attributes payload from updates and responses
def extract_attributes(payload):
    if not isinstance(payload, dict):
        return {}
    
    attrs = {}
    
    if "shared" in payload and isinstance(payload["shared"], dict):
        attrs.update(payload["shared"])
    
    if "client" in payload and isinstance(payload["client"], dict):
        attrs.update(payload["client"])

    if not attrs:
        attrs.update(payload)
    
    return attrs

# Wait until predicate returns True or timeout expires
def wait_for(predicate, timeout_sec=3.0, interval_sec=0.1):
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval_sec)

    return predicate()