from MyMQTT import *
import time, json

class Printer:
    def notify(self, topic, payload):
        try:
            data = json.loads(payload)
        except Exception:
            data = payload.decode() if isinstance(payload, (bytes, bytearray)) else str(payload)
        print(f'Recieved message on topic "{topic}": {data}')

BROKER = "localhost"
PORT   = 1883
TOPIC  = "hello"

client = MyMQTT("subscriber", BROKER, PORT, notifier=Printer())
client.start()
client.mySubscribe(TOPIC)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Subscriber stopped succesfully")
    pass
finally:
    client.stop()