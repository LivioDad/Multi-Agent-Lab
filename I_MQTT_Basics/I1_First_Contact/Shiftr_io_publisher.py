import time, paho.mqtt.client as mqtt

BROKER="localhost"
TOPIC="hello"

def on_message(_, __, msg):
    print(f"[SUB] {msg.topic} -> {msg.payload.decode()}")

c = mqtt.Client()
c.on_message = on_message
c.connect(BROKER, 1883, 60)
c.subscribe(TOPIC)
c.loop_start()

for i in range(50):
    c.publish(TOPIC, f"msg {i}")
    time.sleep(0.5)

time.sleep(2)
c.loop_stop(); c.disconnect()