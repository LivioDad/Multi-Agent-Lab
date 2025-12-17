# II.2 – Dynamic Sensor Network

## Objective
Extend the sensor network to support dynamic behavior:
- Sensors and averaging agents appear and disappear automatically
- Lifecycle management is controlled by `main.py`

## Components
- sensor.py
- averaging_agent.py
- interface_agent_gui.py
- main.py

## MQTT Topics

### Sensor publication
{REFUGE_NAME}/{room}/{measurement_type}/{sensor_id}

### Averaging Agent
- Subscribe: {REFUGE_NAME}/+/{measurement_type}/+
- Publish: {REFUGE_NAME}/AA/{measurement_type}/{agent_id}

### Interface Agent subscription
{REFUGE_NAME}/AA/+/+

## Configuration
Defined in `config.json`:
- `time_sensors`
- `TW_AA`

## Dynamic Behavior
- Agents alternate between ON and OFF states
- Durations are randomly selected within predefined ranges

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

## Execution
1. (Optional) Create and activate a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install paho-mqtt
   ```
2. Start the MQTT broker (e.g. shiftr.io Desktop)
3. Run: ```python3 main.py```

