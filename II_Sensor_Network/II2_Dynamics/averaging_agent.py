import time
import threading
import statistics as stat

import paho.mqtt.client as mqtt


class AveragingAgent:
    """
    Subscribes to:
        {refuge_name}/+/{measurement_type}/+
    collects values for a time window of duration `window_s` (TW_AA),
    computes the average and pubishes it on:
        {refuge_name}/AA/{measurement_type}/{agent_id}
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        refuge_name: str,
        measurement_type: str,
        agent_id: str,
        window_s: float,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name
        self.measurement_type = measurement_type
        self.agent_id = agent_id
        self.window_s = window_s

        self.topic_in = f"{refuge_name}/+/{measurement_type}/+"
        self.topic_out = f"{refuge_name}/AA/{measurement_type}/{agent_id}"

        self.client = mqtt.Client()
        self._stop_event = threading.Event()
        self._values = []
        self._lock = threading.Lock()

    # MQTT callbacks

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        # print(
        #     f"[{self.agent_id}] Connected to MQTT broker ({status}). "
        #     f"Subscribing to: {self.topic_in}"
        # )
        client.subscribe(self.topic_in)

    def _on_message(self, client, userdata, msg):
        try:
            value = float(msg.payload.decode())
        except ValueError:
            # print(f"[{self.agent_id}] Skipping non-numeric payload on {msg.topic}: {msg.payload!r}")
            return

        with self._lock:
            self._values.append(value)

    # Public API

    def connect(self) -> None:
        """Connects to the broker and starts MQTT loop in background."""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def run(self) -> None:
        """Main averaging loop. Blocks until "stop()" is called"""
        self.connect()
        t_start = time.time()
        try:
            while not self._stop_event.is_set():
                now = time.time()
                if now - t_start >= self.window_s:
                    with self._lock:
                        if self._values:
                            avg = round(stat.mean(self._values), 2)
                            self._values.clear()
                        else:
                            avg = None
                    if avg is not None:
                        self.client.publish(self.topic_out, payload=str(avg), qos=0)
                        # print(
                        #     f"[{self.agent_id}] Average {self.measurement_type} "
                        #     f"in last {self.window_s}s -> {avg}"
                        # )
                    t_start = now

                time.sleep(0.1)
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            #print(f"[{self.agent_id}] stopped successfully")

    def stop(self) -> None:
        """Clean stop"""
        self._stop_event.set()
