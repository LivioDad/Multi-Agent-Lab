import paho.mqtt.client as mqtt
import time,json,os,statistics as stat

# Load config.json file
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

TW = config["TW_AA"] # Averaging time window
refuge_name = "refuge_Monviso"
measurement_type = "humidity"
averaging_agent_id = "AA2"

TOPIC_IN = f"{refuge_name}/+/{measurement_type}/+"
print(f"Topic in: {TOPIC_IN}")
TOPIC_OUT = f"{refuge_name}/AA/{measurement_type}/{averaging_agent_id}"

BROKER = "localhost"
PORT = 1883

c = mqtt.Client(client_id=averaging_agent_id)
# Broker connection
c.connect(BROKER,PORT)
print(f"Connected to broker '{BROKER}'")

def on_message(c, userdata, msg):
    payload = float(msg.payload.decode())
    temps_list.append(payload)

c.on_message = on_message
c.subscribe(TOPIC_IN)
    
temps_list = []
c.loop_start()

try:
    t1 = time.time()
    while True:
        if time.time()-t1 >= TW:
            payload = str(stat.mean(temps_list))
            payload = round(float(payload), 2)
            c.publish(TOPIC_OUT,payload=payload)
            print(f"Average {measurement_type} value in the last {TW}s is {payload}")
            temps_list = []
            t1 = time.time()

except KeyboardInterrupt:
    print(f"{averaging_agent_id} stopped succesfully")
finally:
    c.loop_stop()
    c.disconnect()