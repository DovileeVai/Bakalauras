"""Configuration values for the ThingsBoard device simulators."""

import os
from dotenv import load_dotenv

load_dotenv()

BROKER = os.getenv("THINGSBOARD_BROKER", "demo.thingsboard.io")
PORT = int(os.getenv("THINGSBOARD_PORT", "1883"))

SPRINKLER_TOKEN = os.getenv("SPRINKLER_TOKEN")
SOIL_MOISTURE_SENSOR_TOKEN = os.getenv("SOIL_MOISTURE_SENSOR_TOKEN")
TEMPERATURE_SENSOR_TOKEN = os.getenv("TEMPERATURE_SENSOR_TOKEN")
AIR_HUMIDITY_SENSOR_TOKEN = os.getenv("AIR_HUMIDITY_SENSOR_TOKEN")
WATER_FLOW_SENSOR_TOKEN = os.getenv("WATER_FLOW_SENSOR_TOKEN")

TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTR_UPDATES_TOPIC = "v1/devices/me/attributes"
ATTR_REQUEST_TOPIC = "v1/devices/me/attributes/request/{}"
ATTR_RESPONSE_TOPIC = "v1/devices/me/attributes/response/+"