from MyMQTT import *
import time

BROKER = "localhost"
PORT   = 1883
TOPIC  = "hello"
         #(self, clientID, broker, port, notifier):
client = MyMQTT("publisher", BROKER, PORT, notifier=None)
client.start()
msg = "Hi from the MQTT publisher!"

try:
    while True:
        time.sleep(2)
        client.myPublish(TOPIC, msg)
        print(f'Message "{msg}" published on topic {TOPIC}')
except KeyboardInterrupt:
    client.stop()
    print("Publisher stopped succesfully")
    pass
finally:
    client.stop()