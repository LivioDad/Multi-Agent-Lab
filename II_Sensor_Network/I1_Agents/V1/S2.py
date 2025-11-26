import paho.mqtt.client as mqtt
import time, random, json, os

# Load config.json file
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)
time_sensors = config["time_sensors"]

# Sensor parameters that go to automatically build the topic
refuge_name = "refuge_Monviso"
room = "technical_room"
measurement_type = "temperature"
sensor_id = "S2"

TOPIC = f"{refuge_name}/{room}/{measurement_type}/{sensor_id}"
print(f"Topic: {TOPIC}")

BROKER = "localhost"
PORT = 1883

c = mqtt.Client(client_id=sensor_id)

c.connect(BROKER,PORT)
print(f"Connected to broker '{BROKER}'")
c.loop_start()

try:
    while True:
        reading = round(random.uniform(-5, 5), 2)
        payload = str(reading)
        c.publish(TOPIC, payload=payload, qos=0)
        print(f"[published] {TOPIC} <- {payload}")
        time.sleep(time_sensors)

except KeyboardInterrupt:
    print(f"{sensor_id} stopped succesfully")
finally:
    c.loop_stop()
    c.disconnect()