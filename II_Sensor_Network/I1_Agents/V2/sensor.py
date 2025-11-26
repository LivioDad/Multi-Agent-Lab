import time
import random
import threading

import paho.mqtt.client as mqtt


class Sensor:
    """
    Generic MQTT sensor that publishes a random value every "time_sensors" seconds
    on a topic with structure:
        {refuge_name}/{room}/{measurement_type}/{sensor_id}
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        refuge_name: str,
        room: str,
        measurement_type: str,
        sensor_id: str,
        time_sensors: float,
        value_min: float,
        value_max: float,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name
        self.room = room
        self.measurement_type = measurement_type
        self.sensor_id = sensor_id
        self.time_sensors = time_sensors
        self.value_min = value_min
        self.value_max = value_max

        self.topic = f"{refuge_name}/{room}/{measurement_type}/{sensor_id}"
        self.client = mqtt.Client()
        self._stop_event = threading.Event()

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[{self.sensor_id}] Connected to MQTT broker ({status}). Topic: {self.topic}")

    # ---------- Public API ----------

    def connect(self) -> None:
        """Connects to the broker and starts MQTT loop in background."""
        self.client.on_connect = self._on_connect
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def run(self) -> None:
        """Main publishing loop. Blocks until "stop()" is called"""
        self.connect()
        try:
            while not self._stop_event.is_set():
                reading = round(random.uniform(self.value_min, self.value_max), 2)
                payload = str(reading)
                self.client.publish(self.topic, payload=payload, qos=0)
                print(f"[{self.sensor_id}] [published] {self.topic} <- {payload}")

                slept = 0.0
                step = 0.1
                while slept < self.time_sensors and not self._stop_event.is_set():
                    time.sleep(step)
                    slept += step
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"[{self.sensor_id}] stopped successfully")

    def stop(self) -> None:
        """Clean stop"""
        self._stop_event.set()
