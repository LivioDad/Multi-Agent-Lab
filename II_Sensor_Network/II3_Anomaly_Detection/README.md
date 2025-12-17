# II.3 – Anomaly Detection and Identification

## Objective
Enhance the sensor network with anomaly detection and recovery mechanisms:
- Detect abnormal sensor values
- Identify faulty sensors and reset them automatically

## Components
- sensor.py
- averaging_agent.py
- detection_agent.py
- identification_agent.py
- interface_agent_gui.py
- main.py

## MQTT Topics

### Sensor data
{REFUGE_NAME}/{room}/{measurement_type}/{sensor_id}

### Averaging Agent output
{REFUGE_NAME}/AA/{measurement_type}/{agent_id}

### Anomaly alerts
{REFUGE_NAME}/alert/anomaly

### Sensor reset command
{REFUGE_NAME}/cmd/{sensor_id}/reset

## Detection Logic
- Sliding window of recent values
- Mean and standard deviation computation
- Anomaly detected if:
|value - mean| > k × std

## Clients

### Sensor
- room
- measurement_type
- sensor_id
- time_sensors
- value_min, value_max
- can_fail (optional)
- error_probability (optional)
- error_offset (optional)

### Detection Agent
- window_size
- k_sigma

### Identification Agent
- Listens for anomaly alerts and sends RESET commands

## Execution
```bash
pip install paho-mqtt
python3 main.py
```
