import json
import threading
import time

import paho.mqtt.client as mqtt


class IdentificationAgent:
    """
    Identification agent.

    - subscribes to:
        {refuge_name}/alert/anomaly
      where the payload is a JSON object produced by DetectionAgent.

    - for each alert, publishes a RESET command to the corresponding sensor(s)
      on topics:
        {refuge_name}/cmd/<sensor_id>/reset
      with a simple string payload, e.g. "RESET".
    """

    def __init__(self, broker_host: str, broker_port: int, refuge_name: str) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name

        self.topic_in_alerts = f"{refuge_name}/alert/anomaly"
        self.topic_out_cmd_prefix = f"{refuge_name}/cmd"

        self.client = mqtt.Client()
        self._stop_event = threading.Event()

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[ID] Connected to broker ({status}). Subscribing to: {self.topic_in_alerts}")
        client.subscribe(self.topic_in_alerts)

    def _on_message(self, client, userdata, msg):
        try:
            alert = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            print(f"[ID] Invalid JSON alert on {msg.topic}: {msg.payload!r}")
            return

        # Support either "sensor_id" (single) or "sensor_ids" (list)
        sensor_ids = []
        if "sensor_ids" in alert and isinstance(alert["sensor_ids"], list):
            sensor_ids = alert["sensor_ids"]
        elif "sensor_id" in alert:
            sensor_ids = [alert["sensor_id"]]

        if not sensor_ids:
            print(f"[ID] Alert without sensor id(s): {alert}")
            return

        for sensor_id in sensor_ids:
            topic = f"{self.topic_out_cmd_prefix}/{sensor_id}/reset"
            self.client.publish(topic, payload="RESET", qos=0)
            print(f"[ID] Sent RESET to {sensor_id} on topic {topic}")

    # ---------- Public API ----------

    def connect(self) -> None:
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def run(self) -> None:
        self.connect()
        try:
            while not self._stop_event.is_set():
                time.sleep(0.1)
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("[ID] stopped successfully")

    def stop(self) -> None:
        self._stop_event.set()
