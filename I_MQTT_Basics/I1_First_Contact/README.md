# I.1 – First Contact (MQTT Basics)

## Objective
The objective of this exercise is to verify that the MQTT environment is correctly set up and to
become familiar with the basic publish/subscribe communication model.

### MyMQTT.py
`MyMQTT.py` is a pre developped simple abstraction layer on top of the `paho-mqtt` library.
It contains the connection to the broker, the subscription and publication mechanisms and the callback handling for received messages.

### Publisher.py
`Publisher.py` implements a basic MQTT publisher using the `MyMQTT` abstraction.
The client:
- connects to the broker
- periodically publishes a message on a predefined topic

### Subscriber.py
`Subscriber.py` implements an MQTT subscriber based on `MyMQTT`.
It uses a notifier object to handle received messages and prints them on the console.
The client:
- connects to the broker
- subscribes to a topic
- displays any received message

### Shiftr_io_publisher.py
`Shiftr_io_publisher.py` is a minimal MQTT client directly implemented using the `paho-mqtt` library,
without relying on the `MyMQTT` abstraction (to give a different and more straightforward example).

Its purpose is mainly to:
- quickly validate the MQTT broker configuration
- visualize published messages in the Shiftr.io graphical interface

## Parameters
The MQTT clients can be configured using the following parameters:
- Broker address: hostname or IP address of the MQTT broker (default: `localhost`)
- Broker port: MQTT port (default: `1883`)
- Topic name: MQTT topic used for publish/subscribe
- Publish period: delay between two consecutive message publications (in seconds)

## How to run 
1. (Optional) Create and activate a Python virtual environment:
bash
   python -m venv .venv
   source .venv/bin/activate
   pip install paho-mqtt

2. Start the MQTT broker (e.g. shiftr.io Desktop)
3a. Run the python script Shiftr_io_publisher.py and look at the GUI in the Shiftr.io app
3b. Run the python script Publisher.py and than Subscriber.py(in a separated terminal) and check the console output