import json
import os
import threading
import time

from sensor import Sensor
from averaging_agent import AveragingAgent


BROKER_HOST = "localhost"
BROKER_PORT = 1883
REFUGE_NAME = "refuge_Monviso"

# ---- Load config.json ----
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

TIME_SENSORS = config["time_sensors"]
TW_AA = config["TW_AA"]

# ---- Configurations of sensors ----
SENSORS = [
    dict(sensor_id="S1",  room="turbine",        measurement_type="power",       value_min=1000.0, value_max=2000.0),
    dict(sensor_id="S2",  room="technical_room", measurement_type="temperature", value_min=-5.0,   value_max=5.0),
    dict(sensor_id="S3",  room="technical_room", measurement_type="temperature", value_min=5.0,    value_max=13.0),
    dict(sensor_id="S4",  room="dormitory",      measurement_type="temperature", value_min=15.0,   value_max=25.0),
    dict(sensor_id="S5",  room="kitchen",        measurement_type="temperature", value_min=15.0,   value_max=25.0),
    dict(sensor_id="S6",  room="kitchen",        measurement_type="humidity",    value_min=20.0,   value_max=85.0),
    dict(sensor_id="S7",  room="outdoor",        measurement_type="temperature", value_min=-10.0,  value_max=5.0),
    dict(sensor_id="S8",  room="outdoor",        measurement_type="humidity",    value_min=10.0,   value_max=100.0),
    dict(sensor_id="S9",  room="outdoor",        measurement_type="wind_speed",  value_min=0.0,    value_max=20.0),
    dict(sensor_id="S10", room="kitchen",        measurement_type="power",       value_min=500.0,  value_max=900.0),
]

# ---- Configurations of Averaging Agents ----
AVERAGING_AGENTS = [
    dict(agent_id="AA1", measurement_type="temperature"),
    dict(agent_id="AA2", measurement_type="humidity"),
    dict(agent_id="AA3", measurement_type="power"),
]


def main():
    sensors = []
    agents = []
    threads = []

    # Create Sensor objects
    for s in SENSORS:
        sensor = Sensor(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            refuge_name=REFUGE_NAME,
            room=s["room"],
            measurement_type=s["measurement_type"],
            sensor_id=s["sensor_id"],
            time_sensors=TIME_SENSORS,
            value_min=s["value_min"],
            value_max=s["value_max"],
        )
        sensors.append(sensor)
        t = threading.Thread(target=sensor.run, name=f"sensor-{s['sensor_id']}", daemon=True)
        threads.append(t)

    # Create AveragingAgent objects
    for aa in AVERAGING_AGENTS:
        agent = AveragingAgent(
            broker_host=BROKER_HOST,
            broker_port=BROKER_PORT,
            refuge_name=REFUGE_NAME,
            measurement_type=aa["measurement_type"],
            agent_id=aa["agent_id"],
            window_s=TW_AA,
        )
        agents.append(agent)
        t = threading.Thread(target=agent.run, name=f"agent-{aa['agent_id']}", daemon=True)
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    print("All sensors and averaging agents started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all components...")
        for s in sensors:
            s.stop()
        for a in agents:
            a.stop()

        time.sleep(2)
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
