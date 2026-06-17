# IoT Device Data Anomaly Detection

This project simulates a smart irrigation system, collects IoT device data, prepares datasets, injects predefined anomalies, and applies anomaly detection methods to evaluate their performance.

This simulated system consists of separate Python-based device simulators: a temperature sensor, an air humidity sensor, a soil moisture sensor, a water flow sensor, and a sprinkler actuator. The generated telemetry is sent to the ThingsBoard platform using MQTT and is also stored locally in CSV files for further processing and analysis.

The anomaly detection experiments are performed using the PyOD library. Three methods are applied and compared: K-nearest neighbors (KNN), Local Outlier Factor (LOF), and Isolation Forest (iForest).

---

# Project Structure

The `devices/` directory contains the Python simulators for the smart irrigation system components. Each simulator generates values for one device and sends telemetry data to ThingsBoard. The same generated values are also saved into local CSV files.

The `data/` directory contains raw and processed datasets. Raw data from individual simulators is stored in `data/raw/`, while prepared datasets used for anomaly detection experiments are stored in `data/processed/`.

The `analysis/` directory contains scripts for applying anomaly detection methods. The main experiment scripts are `knn.py`, `lof.py`, and `isolation_forest.py`.

The `results/` directory contains CSV files with method predictions and evaluation results.

The main data preparation scripts are:

- `prepare_normal_dataset.py` - merges raw device CSV files into a common dataset;
- `inject_anomalies.py` - injects predefined anomalies into the evaluation dataset;
- `add_derived_features.py` - adds derived soil moisture features used in the experiments.

---

# Simulated System

The project simulates a smart irrigation scenario. Under normal conditions, the watering state depends on soil moisture. When soil moisture becomes too low, watering can be enabled. During watering, water flow should be detected and soil moisture should increase. When watering is disabled, water flow should be zero and soil moisture may decrease.

This scenario is used to generate multivariate IoT data where anomalies can appear as individual unusual values, inconsistent device states, or unusual changes over time.

---

# ThingsBoard Configuration

The simulators send telemetry data to [ThingsBoard](https://thingsboard.io/) using MQTT. Configuration values are loaded from the `.env` file in `config.py`.

Example `.env` file:

```env
THINGSBOARD_BROKER=demo.thingsboard.io
THINGSBOARD_PORT=1883

SPRINKLER_TOKEN=your_sprinkler_token
SOIL_MOISTURE_SENSOR_TOKEN=your_soil_moisture_sensor_token
TEMPERATURE_SENSOR_TOKEN=your_temperature_sensor_token
AIR_HUMIDITY_SENSOR_TOKEN=your_air_humidity_sensor_token
WATER_FLOW_SENSOR_TOKEN=your_water_flow_sensor_token
```

The MQTT topics used by the simulators are defined in `config.py`:

```python
TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTR_UPDATES_TOPIC = "v1/devices/me/attributes"
ATTR_REQUEST_TOPIC = "v1/devices/me/attributes/request/{}"
ATTR_RESPONSE_TOPIC = "v1/devices/me/attributes/response/+"
```

---

# How to Run the Project

Install the required dependencies:

```bash
pip install -r requirements.txt
```

To run the device simulators separately:

```bash
python -m devices.temperature_sensor
python -m devices.air_humidity_sensor
python -m devices.soil_moisture_sensor
python -m devices.water_flow_sensor
python -m devices.sprinkler
```

To run all devices at once:

```bash
python run_devices.py
```

The simulators require ThingsBoard device access tokens to be configured in the `.env` file.

After collecting raw data, prepare the normal dataset:

```bash
python prepare_normal_dataset.py
```

Inject modeled anomalies:

```bash
python inject_anomalies.py
```

Add  derived features:

```bash
python add_derived_features.py
```

Run anomaly detection experiments:

```bash
python -m analysis.knn
python -m analysis.lof
python -m analysis.isolation_forest
```

---

# Modeled Anomalies

The anomaly injection logic is implemented in `inject_anomalies.py`.

The following anomaly types are injected into the evaluation dataset:

- `temperature_spike` - short temperature spike anomalies;
- `flow_while_not_watering` - water flow is detected while watering is disabled;
- `no_flow_while_watering` - watering is enabled, but no water flow is detected;
- `stuck_soil_moisture_sensor` - soil moisture sensor remains constant for a longer period;
- `watering_without_soil_moisture_response` - watering is enabled, but soil moisture does not increase as expected.

The number and duration of injected anomalies are controlled by constants in `inject_anomalies.py`. Example:

```python
RANDOM_SEED = 42

NO_FLOW_LENGTH = 25
FLOW_WHILE_OFF_LENGTH = 35
STUCK_SENSOR_LENGTH = 60
NO_SOIL_RESPONSE_LENGTH = 25

TEMPERATURE_SPIKE_LENGTH = 1
TEMPERATURE_SPIKE_POSITIONS = [0.55, 0.60, 0.65, 0.70, 0.75]
TEMPERATURE_SPIKE_VALUE = 60.0
```

These parameters define how anomalies are injected into the evaluation dataset. For example, the stuck soil moisture sensor anomaly is injected as a longer 60-row segment, while temperature spike anomalies are injected as five short one-row events at predefined positions in the dataset.

In total, 150 anomalies are injected into the evaluation dataset. 

The anomaly labels are stored in the following columns:

- `is_anomaly`;
- `anomaly_type`.

These labels are used only for evaluation and are not used as input features for the anomaly detection methods.

---

# Derived Features

Derived soil moisture features are created in `add_derived_features.py`. They are used to describe soil moisture changes over time, because some modeled anomalies can not be described well using only the current soil moisture value.

The following derived features are added:

- `soil_moisture_change` - change in soil moisture compared to the previous measurement;
- `soil_moisture_change_10` - change in soil moistur over a 10 measurements window;
- `soil_moisture_std_10` - soil moisture variability over a 10 measurements window.

The rolling window size used for these features is 10 measurements.

---

# Anomaly Detection Experiments

The anomaly detection experiments are implemented in the `analysis/` directory. The training and testing dataset paths are defined in `analysis/utils.py`.

Two feature sets are used in th eexperiments.

Base features:

```python
BASE_FEATURES = [
    "temperature",
    "air_humidity",
    "soil_moisture",
    "water_flow",
    "watering",
]
```

Base features with derived soil moisture features:

```python
ALL_FEATURES = [
    "temperature",
    "air_humidity",
    "soil_moisture",
    "water_flow",
    "watering",
    "soil_moisture_change",
    "soil_moisture_change_10",
    "soil_moisture_std_10",
]
```

The expected anomaly proportion is defined as:
```python
CONTAMINATION = 0.042
```

This value is based on 150 inserted anomalies in the evaluation dataset after skipping the first 10 rows.

## KNN

KNN experiments are implemented in `analysis/knn.py`. The following neighbor values are tested:

```python
N_NEIGHBORS_VALUES = [5, 10, 20, 30, 40, 50]
```

## LOF

LOF experiments are implemented in `analysis/lof.py`. The following neighbor values are tested:

```python
N_NEIGHBORS_VALUES = [5, 10, 20, 30, 40, 50, 75, 100]
```

## iForest

iForest experiments are implemented in `analysis/isolation_forest.py`. A fixed random state is used for reproducibility:

```python
RANDOM_STATE = 42
```

The scripts print evaluation metrics to the terminal and save detailed prediction results as CSV files in the `results/` directory.

---

# Evaluation

The evaluation logic is implemented in `analysis/utils.py`. The methods are evaluated using precision, recall and F1-score.

The results are also analyzed by anomaly type to determine which types of anomalies each method detects better or worse.


---


# Author

Dovilė Vaiginytė