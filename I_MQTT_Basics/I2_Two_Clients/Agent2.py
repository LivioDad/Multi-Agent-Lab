import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
SLEEP = 1 # s

def main(role):
    other  = "pong" if role == "ping" else "ping"
    inbox  = "topic1" if role == "ping" else "topic2"
    outbox = "topic2" if role == "ping" else "topic1"

    client = mqtt.Client(client_id=f"{role}")

    def on_connect(c, _u, _f, rc, _p=None):
        print(f"[{role}] connected rc={rc} — subscribe {inbox}")
        c.subscribe(inbox)

    def on_message(c, _u, msg):
        payload = msg.payload.decode()
        print(f"[{role}] < {msg.topic}: {payload}")
        if payload == other:
            time.sleep(SLEEP)
            c.publish(outbox, role)
            print(f"[{role}] > {outbox}: {role}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)

    if role == "ping":
        client.publish(outbox, "ping")
        print(f"[{role}] > {outbox}: ping (kick)")

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"{role} stopped succesfully")
        client.disconnect()

if __name__ == "__main__":
    role = "ping"
    main(role)
