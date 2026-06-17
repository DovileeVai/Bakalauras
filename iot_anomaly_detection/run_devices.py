"""Start and stop all IoT device simulators."""

import subprocess
import time

DEVICE_MODULES = [
    "devices.sprinkler",
    "devices.soil_moisture_sensor",
    "devices.temperature_sensor",
    "devices.air_humidity_sensor",
    "devices.water_flow_sensor",
]

SHUTDOWN_TIMEOUT_SECONDS = 8.0

def main():
    processes = []

    try:
        for module in DEVICE_MODULES:
            print(f"Starting {module}...")
            process = subprocess.Popen(["python", "-m", module])
            processes.append(process)
            time.sleep(0.5)

        print("All devices started. Press Ctrl+C to stop.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping all devices...")

        end_time = time.time() + SHUTDOWN_TIMEOUT_SECONDS

        while time.time() < end_time:
            still_running = [p for p in processes if p.poll() is None]

            if not still_running:
                break
            time.sleep(0.2)

        for process in processes:
            if process.poll() is None:
                process.terminate()

        for process in processes:
            process.wait()

        print("All devices stopped.")
    
if __name__ == "__main__":
    main()