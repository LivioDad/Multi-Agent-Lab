import json
import threading
import time
import statistics as stat
from collections import defaultdict

import paho.mqtt.client as mqtt


class DetectionAgent:
    """
    Detection agent.

    - subscribes to:
        {refuge_name}/+/+/+
      which covers both:
        {refuge_name}/<room>/<measurement_type>/<sensor_id>  (raw readings)
        {refuge_name}/AA/<measurement_type>/<agent_id>       (averages)

    - publishes alerts on:
        {refuge_name}/alert/anomaly

      Payload example:
        {
          "measurement_type": "...",
          "sensor_id": "...",
          "room": "...",
          "value": <float>,
          "mean": <float>,
          "stdev": <float>,
          "k_sigma": 2.0,
          "timestamp": <float>,
          "last_average": <float or null>
        }

    A reading is considered anomalous if it is more than k_sigma standard
    deviations away from the mean of the last `window_size` readings
    of the same measurement_type.
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        refuge_name: str,
        window_size: int = 50,
        k_sigma: float = 2.0,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name
        self.window_size = window_size
        self.k_sigma = k_sigma

        # Topics
        self.topic_all = f"{refuge_name}/+/+/+"
        self.topic_alerts = f"{refuge_name}/alert/anomaly"

        self.client = mqtt.Client()
        self._stop_event = threading.Event()

        # History of readings per measurement_type
        self._values_by_type: dict[str, list[float]] = defaultdict(list)
        # Last average per measurement_type (optional, for information only)
        self._last_avg_by_type: dict[str, float] = {}
        self._lock = threading.Lock()

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[DETECT] Connected to broker ({status}).")
        print(f"[DETECT] Subscribing to: {self.topic_all}")
        client.subscribe(self.topic_all)

    def _on_message(self, client, userdata, msg):
        topic_parts = msg.topic.split("/")
        if len(topic_parts) != 4:
            print(f"[DETECT] Unexpected topic format: {msg.topic}")
            return

        try:
            value = float(msg.payload.decode())
        except ValueError:
            print(f"[DETECT] Non-numeric payload on {msg.topic}: {msg.payload!r}")
            return

        refuge, second, measurement_type, last = topic_parts

        if second == "AA":
            # Average from AveragingAgent: refuge/AA/<measurement_type>/<agent_id>
            agent_id = last
            with self._lock:
                self._last_avg_by_type[measurement_type] = value
            print(f"[DETECT] New average from {agent_id} for {measurement_type}: {value}")
        else:
            # Raw sensor reading: refuge/<room>/<measurement_type>/<sensor_id>
            room = second
            sensor_id = last
            self._process_reading(measurement_type, sensor_id, value, room)

    # ---------- Internal helpers ----------

    def _process_reading(self, measurement_type: str, sensor_id: str, value: float, room: str) -> None:
        with self._lock:
            values = self._values_by_type[measurement_type]
            values.append(value)
            if len(values) > self.window_size:
                # Keep a bounded history
                values.pop(0)

            if len(values) < 2:
                # Not enough data yet to compute a standard deviation
                return

            mean = stat.mean(values)
            stdev = stat.stdev(values)
            if stdev == 0:
                return

            distance = abs(value - mean)
            if distance > self.k_sigma * stdev:
                # Anomaly detected
                alert = {
                    "measurement_type": measurement_type,
                    "sensor_id": sensor_id,
                    "room": room,
                    "value": value,
                    "mean": mean,
                    "stdev": stdev,
                    "k_sigma": self.k_sigma,
                    "timestamp": time.time(),
                    # Optional: also include last published average if we have it
                    "last_average": self._last_avg_by_type.get(measurement_type),
                }
                payload = json.dumps(alert)
                self.client.publish(self.topic_alerts, payload=payload, qos=0)
                print(
                    f"[DETECT] Anomaly detected for sensor {sensor_id} ({measurement_type}): "
                    f"value={value:.2f}, mean={mean:.2f}, stdev={stdev:.2f}"
                )

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
            print("[DETECT] stopped successfully")

    def stop(self) -> None:
        self._stop_event.set()
