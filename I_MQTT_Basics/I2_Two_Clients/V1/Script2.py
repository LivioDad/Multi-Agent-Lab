import time, paho.mqtt.client as mqtt

AGENT_ROLE = "pong"

OTHER_AGENT_ROLE = "pong" if AGENT_ROLE == "ping" else "ping"
BROKER="localhost"
TOPIC1="topic1" if AGENT_ROLE == "ping" else "topic2"
TOPIC2="topic2" if AGENT_ROLE == "pong" else "topic1"

def on_message(_, __, msg):
    print(f"[SUB] {msg.topic} -> {msg.payload.decode()}")
    return msg.payload.decode()

c = mqtt.Client()
c.on_message = on_message
c.connect(BROKER, 1883, 60)
c.subscribe(TOPIC1)

if AGENT_ROLE == "pong":
    c.publish(TOPIC2, "ping")

while True:
    try:
        if on_message == AGENT_ROLE:
            c.publish(TOPIC2, OTHER_AGENT_ROLE)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Ping-Pong stopped")
        c.disconnect() 
    