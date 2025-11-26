import time
import random
import threading

import paho.mqtt.client as mqtt


class Sensor:
    """
    Generic MQTT sensor that publishes a random value every "time_sensors" seconds
    on a topic with structure:
        {refuge_name}/{room}/{measurement_type}/{sensor_id}

    It also listens on:
        {refuge_name}/cmd/{sensor_id}/reset

    When it receives a "RESET" command on that topic, it resets its internal
    fault configuration (if any).
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
        # optional fault configuration for anomaly detection)
        can_fail: bool = False,
        error_probability: float = 0.2,
        error_offset: float = 20.0,
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

        # Fault behaviour configuration
        self.can_fail = can_fail
        self.error_probability = error_probability
        self.error_offset = error_offset

        self.topic = f"{refuge_name}/{room}/{measurement_type}/{sensor_id}"
        self.reset_topic = f"{refuge_name}/cmd/{sensor_id}/reset"

        self.client = mqtt.Client()
        self._stop_event = threading.Event()

    # MQTT callbacks

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[{self.sensor_id}] Connected to MQTT broker ({status}). Topic: {self.topic}")
        # Subscribe to reset command
        client.subscribe(self.reset_topic)
        print(f"[{self.sensor_id}] Subscribed to reset topic: {self.reset_topic}")

    def _on_message(self, client, userdata, msg):
        if msg.topic == self.reset_topic:
            command = msg.payload.decode().strip().upper()
            if command == "RESET":
                self._handle_reset()

    def _handle_reset(self) -> None:
        """
        Handle a RESET command.
        For this exercise we simply disable the faulty behaviour and print a log.
        """
        print(f"[{self.sensor_id}] Received RESET command -> disabling faulty mode.")
        self.can_fail = False

    # Public API

    def connect(self) -> None:
        """Connects to the broker and starts MQTT loop in background."""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def _generate_reading(self) -> float:
        """
        Generate either a normal reading in [value_min, value_max]
        or (with some probability) an erroneous reading far from the range.
        """
        # Normal reading
        reading = random.uniform(self.value_min, self.value_max)

        # Occasionally generate erroneous readings if can_fail is True
        if self.can_fail and random.random() < self.error_probability:
            # Push the value far away from the normal range
            direction = random.choice([-1.0, 1.0])
            span = self.value_max - self.value_min
            reading = ((self.value_min + self.value_max) / 2.0) + direction * (span + self.error_offset)
            # print(f"[{self.sensor_id}] Generating ERRONEOUS value: {reading:.2f}")

        return round(reading, 2)

    def run(self) -> None:
        """Main publishing loop. Blocks until "stop()" is called"""
        self.connect()
        try:
            while not self._stop_event.is_set():
                reading = self._generate_reading()
                payload = str(reading)
                self.client.publish(self.topic, payload=payload, qos=0)
                # print(f"[{self.sensor_id}] [published] {self.topic} <- {payload}")

                slept = 0.0
                step = 0.1
                while slept < self.time_sensors and not self._stop_event.is_set():
                    time.sleep(step)
                    slept += step
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            # print(f"[{self.sensor_id}] stopped successfully")

    def stop(self) -> None:
        """Clean stop"""
        self._stop_event.set()
