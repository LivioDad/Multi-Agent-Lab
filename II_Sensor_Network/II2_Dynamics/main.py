import json
import os
import threading
import time
import random

from sensor import Sensor
from averaging_agent import AveragingAgent
from multiprocessing import Process
from interface_agent_gui import main as gui_main


BROKER_HOST = "localhost"
BROKER_PORT = 1883
REFUGE_NAME = "refuge_Monviso"


# Load configuration file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

TIME_SENSORS = config["time_sensors"]
TW_AA = config["TW_AA"]

# Possible sensors
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


# Possible averaging agents
AVERAGING_AGENTS = [
    dict(agent_id="AA1", measurement_type="temperature"),
    dict(agent_id="AA2", measurement_type="humidity"),
    dict(agent_id="AA3", measurement_type="power"),
]

# Dynamics timing ranges (random ON/OFF periods)
SENSOR_ON_RANGE = (5 * TIME_SENSORS, 15 * TIME_SENSORS)
SENSOR_OFF_RANGE = (1 * TIME_SENSORS, 5 * TIME_SENSORS)

AA_ON_RANGE = (3 * TW_AA, 6 * TW_AA)
AA_OFF_RANGE = (1 * TW_AA, 3 * TW_AA)


# Small helper to allow interruption during sleep
def sleep_interruptible(total, stop_event, step=0.5):
    end = time.time() + total
    while time.time() < end and not stop_event.is_set():
        time.sleep(min(step, end - time.time()))


# Sensor life-cycle: randomly appears and disappears
def sensor_lifecycle(cfg, stop_event):
    sid = cfg["sensor_id"]

    while not stop_event.is_set():

        # OFF state
        off_t = random.uniform(*SENSOR_OFF_RANGE)
        print(f"[DYNAMICS] Sensor {sid} OFF for {off_t:.1f}s")
        sleep_interruptible(off_t, stop_event)
        if stop_event.is_set():
            break

        # ON state 
        sensor = Sensor(
            BROKER_HOST,
            BROKER_PORT,
            REFUGE_NAME,
            cfg["room"],
            cfg["measurement_type"],
            cfg["sensor_id"],
            TIME_SENSORS,
            cfg["value_min"],
            cfg["value_max"],
        )
        t = threading.Thread(target=sensor.run, daemon=True)
        t.start()

        print(f"[DYNAMICS] Sensor {sid} ENTERS the system")

        on_t = random.uniform(*SENSOR_ON_RANGE)
        sleep_interruptible(on_t, stop_event)

        print(f"[DYNAMICS] Sensor {sid} LEAVES the system")
        sensor.stop()
        t.join(timeout=1.5)


# Averaging Agent life-cycle

def aa_lifecycle(cfg, stop_event):
    aid = cfg["agent_id"]

    while not stop_event.is_set():

        # OFF state
        off_t = random.uniform(*AA_OFF_RANGE)
        print(f"[DYNAMICS] AveragingAgent {aid} OFF for {off_t:.1f}s")
        sleep_interruptible(off_t, stop_event)
        if stop_event.is_set():
            break

        # ON state
        agent = AveragingAgent(
            BROKER_HOST,
            BROKER_PORT,
            REFUGE_NAME,
            cfg["measurement_type"],
            cfg["agent_id"],
            TW_AA,
        )
        t = threading.Thread(target=agent.run, daemon=True)
        t.start()

        print(f"[DYNAMICS] AveragingAgent {aid} ENTERS the system")

        on_t = random.uniform(*AA_ON_RANGE)
        sleep_interruptible(on_t, stop_event)

        print(f"[DYNAMICS] AveragingAgent {aid} LEAVES the system")
        agent.stop()
        t.join(timeout=1.5)


# MAIN

def main():
    print("[MAIN] Starting dynamic system...")

    stop_event = threading.Event()

    # Start GUI in separate process
    num_aa = len(AVERAGING_AGENTS)
    gui_process = Process(target=gui_main, args=(num_aa,))
    gui_process.start()


    lifecycle_threads = []

    # Launch sensor lifecycle managers
    for cfg in SENSORS:
        t = threading.Thread(
            target=sensor_lifecycle,
            args=(cfg, stop_event),
            daemon=True
        )
        t.start()
        lifecycle_threads.append(t)

    # Launch averaging agent lifecycle managers
    for cfg in AVERAGING_AGENTS:
        t = threading.Thread(
            target=aa_lifecycle,
            args=(cfg, stop_event),
            daemon=True
        )
        t.start()
        lifecycle_threads.append(t)

    print("[MAIN] Dynamics running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping everything...")
        stop_event.set()

        gui_process.terminate()
        gui_process.join()

        for t in lifecycle_threads:
            t.join(timeout=2)

        print("[MAIN] Shutdown complete.")


if __name__ == "__main__":
    main()
