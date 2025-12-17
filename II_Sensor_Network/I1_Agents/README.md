# II.1 – Sensor Network Agents

## Objective
Implement a basic MQTT-based sensor network composed of:
- Sensor clients publishing measurements
- Averaging Agents (AA) computing averages over time windows
- Interface Agent (IA) displaying aggregated data

## Implementations
Two implementations are provided:
- V1: one script per client (simple, static)
- V2: modular and scalable implementation using classes

## MQTT Topics

### Sensor publication
{REFUGE_NAME}/{room}/{measurement_type}/{sensor_id}

### Averaging Agent subscription
{REFUGE_NAME}/+/{measurement_type}/+

### Averaging Agent publication
{REFUGE_NAME}/AA/{measurement_type}/{agent_id}

### Interface Agent subscription
{REFUGE_NAME}/AA/+/+

## Configuration
Defined in `config.json`:
- `time_sensors`: sensor publication period (s)
- `TW_AA`: averaging time window (s)

## Clients

### Sensor
- room
- measurement_type
- sensor_id
- time_sensors
- value_min, value_max

### Averaging Agent
- measurement_type
- agent_id
- window_s

### Interface Agent
- GUI displaying all averages

## Execution
```bash
1. (Optional) Create and activate a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install paho-mqtt
   ```

2. Start the MQTT broker (e.g. shiftr.io Desktop)
3a. To run V1: ```sensors_start.bat```
3b. To run V2: ```python3 main.py```
