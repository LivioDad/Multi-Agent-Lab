import json
import os
import queue
import time
import tkinter as tk
from tkinter import ttk

import paho.mqtt.client as mqtt


BROKER_HOST = "localhost"
BROKER_PORT = 1883
REFUGE_NAME = "refuge_Monviso"

# Load config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

REFRESH_PERIOD_S = config["TW_AA"]


class InterfaceAgent:
    """
    Agent that receives messages from the broker and sends simple events to the graphic interface
    """

    def __init__(self, broker_host: str, broker_port: int, refuge_name: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name

        self.topic_all_four = f"{refuge_name}/+/+/+"
        self.topic_alerts = f"{refuge_name}/alert/anomaly"

        self.client = mqtt.Client()
        self.queue: "queue.Queue[dict]" = queue.Queue()

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[IA] Connected to MQTT broker ({status}).")
        print(f"[IA] Subscribing to: {self.topic_all_four} and {self.topic_alerts}")
        client.subscribe(self.topic_all_four)
        client.subscribe(self.topic_alerts)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        parts = topic.split("/")

        if topic == self.topic_alerts:
            try:
                alert = json.loads(msg.payload.decode())
            except json.JSONDecodeError:
                print(f"[IA] Invalid JSON alert on {topic}: {msg.payload!r}")
                return

            event = {
                "type": "alert",
                "sensor_id": alert.get("sensor_id"),
                "room": alert.get("room"),
                "measurement_type": alert.get("measurement_type"),
                "value": alert.get("value"),
                "mean": alert.get("mean"),
                "stdev": alert.get("stdev"),
                "timestamp": alert.get("timestamp", time.time()),
            }
            self.queue.put(event)
            return

        if len(parts) != 4:
            return

        refuge, second, measurement_type, last = parts

        if second == "AA":
            try:
                value = float(msg.payload.decode())
            except ValueError:
                print(f"[IA] Skipping non numeric average on {topic}: {msg.payload!r}")
                return

            event = {
                "type": "average",
                "measurement_type": measurement_type,
                "agent_id": last,
                "value": value,
                "timestamp": time.time(),
            }
            self.queue.put(event)
            return

        if second == "cmd" and last == "reset":
            sensor_id = measurement_type
            event = {
                "type": "reset",
                "sensor_id": sensor_id,
                "timestamp": time.time(),
            }
            self.queue.put(event)
            return

        room = second
        sensor_id = last
        try:
            value = float(msg.payload.decode())
        except ValueError:
            print(f"[IA] Skipping non numeric sensor value on {topic}: {msg.payload!r}")
            return

        event = {
            "type": "sensor_value",
            "sensor_id": sensor_id,
            "room": room,
            "measurement_type": measurement_type,
            "value": value,
            "timestamp": time.time(),
        }
        self.queue.put(event)

    def connect(self) -> None:
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        print("[IA] stopped successfully")


class InterfaceGUI:
    """
    Graphic interface with two tables
    One table shows averages from agents
    One table shows sensor status
    """

    def __init__(self, root: tk.Tk, ia: InterfaceAgent, refresh_period_s: int = REFRESH_PERIOD_S, averages_height: int = 5, sensors_height: int = 10):
        self.root = root
        self.ia = ia
        self.refresh_period_s = refresh_period_s
        self.total_reset_sent = 0

        self.root.title("Refuge monitoring")

        averages_label = ttk.Label(root, text="Averages from agents")
        averages_label.pack(padx=10, pady=(10, 0), anchor="w")

        avg_columns = ("measurement_type", "agent_id", "value", "timestamp")
        self.avg_tree = ttk.Treeview(root, columns=avg_columns, show="headings", height=averages_height)
        self.avg_tree.heading("measurement_type", text="Measurement type")
        self.avg_tree.heading("agent_id", text="Agent")
        self.avg_tree.heading("value", text="Last average")
        self.avg_tree.heading("timestamp", text="Timestamp")

        self.avg_tree.column("measurement_type", width=150, anchor="center")
        self.avg_tree.column("agent_id", width=80, anchor="center")
        self.avg_tree.column("value", width=100, anchor="center")
        self.avg_tree.column("timestamp", width=160, anchor="center")

        self.avg_tree.pack(fill="x", expand=False, padx=10, pady=(5, 10))

        sensors_label = ttk.Label(root, text="Sensors status")
        sensors_label.pack(padx=10, pady=(0, 0), anchor="w")

        sensor_columns = ("sensor_id", "room", "measurement_type", "last_value", "status", "last_event")
        self.sensor_tree = ttk.Treeview(root, columns=sensor_columns, show="headings", height=sensors_height)
        self.sensor_tree.heading("sensor_id", text="Sensor")
        self.sensor_tree.heading("room", text="Room")
        self.sensor_tree.heading("measurement_type", text="Measurement type")
        self.sensor_tree.heading("last_value", text="Last value")
        self.sensor_tree.heading("status", text="Status")
        self.sensor_tree.heading("last_event", text="Last event")

        self.sensor_tree.column("sensor_id", width=80, anchor="center")
        self.sensor_tree.column("room", width=100, anchor="center")
        self.sensor_tree.column("measurement_type", width=140, anchor="center")
        self.sensor_tree.column("last_value", width=100, anchor="center")
        self.sensor_tree.column("status", width=100, anchor="center")
        self.sensor_tree.column("last_event", width=160, anchor="center")

        self.sensor_tree.tag_configure("OK", background="")
        self.sensor_tree.tag_configure("FAULTY", background="#ffcccc")
        self.sensor_tree.tag_configure("RESET_SENT", background="#ccffcc")

        self.sensor_tree.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.status_label = ttk.Label(root, text="No data yet")
        self.status_label.pack(pady=(0, 10))

        self.avg_items: dict[tuple[str, str], str] = {}
        self.sensor_items: dict[str, str] = {}
        self.sensors_state: dict[str, dict] = {}

        self.has_avg_data = False
        self.next_expected_time: float | None = None

        self.root.after(200, self._process_queue)
        self.root.after(1000, self._update_status_label)

    def _now(self) -> float:
        return time.time()

    def _reset_expected_time(self):
        self.next_expected_time = self._now() + self.refresh_period_s

    def _schedule_reset_clear(self, sensor_id: str):
        # After 5 seconds the sensor returns to normal status
        def clear_status():
            state = self.sensors_state.get(sensor_id)
            if state is None:
                return
            # If status is still RESET_SENT, turn it back to normal
            if state["status"] == "RESET_SENT":
                state["status"] = "OK"
                self._update_sensor_row(sensor_id)

        # run after 5000 milliseconds
        self.root.after(5000, clear_status)

    def _format_timestamp(self, ts: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    def _ensure_sensor_entry(self, sensor_id: str, room: str | None = None,
                             measurement_type: str | None = None) -> dict:
        state = self.sensors_state.get(sensor_id)
        if state is None:
            state = {
                "sensor_id": sensor_id,
                "room": room or "?",
                "measurement_type": measurement_type or "?",
                "last_value": "",
                "status": "OK",
                "last_event": "",
            }
            self.sensors_state[sensor_id] = state
            item_id = self.sensor_tree.insert(
                "",
                "end",
                values=(
                    state["sensor_id"],
                    state["room"],
                    state["measurement_type"],
                    state["last_value"],
                    state["status"],
                    state["last_event"],
                ),
                tags=(state["status"],),
            )
            self.sensor_items[sensor_id] = item_id
        else:
            if room is not None:
                state["room"] = room
            if measurement_type is not None:
                state["measurement_type"] = measurement_type
        return state

    def _update_sensor_row(self, sensor_id: str):
        state = self.sensors_state[sensor_id]
        item_id = self.sensor_items[sensor_id]
        self.sensor_tree.item(
            item_id,
            values=(
                state["sensor_id"],
                state["room"],
                state["measurement_type"],
                state["last_value"],
                state["status"],
                state["last_event"],
            ),
            tags=(state["status"],),
        )

    def _update_status_label(self):
        total = len(self.sensors_state)
        reset_sent = self.total_reset_sent

        if total == 0:
            msg = "No sensor data yet"
        else:
            msg = f"Sensors: {total} - Reset sent: {reset_sent}"
            if self.has_avg_data and self.next_expected_time is not None:
                remaining = int(round(self.next_expected_time - self._now()))
                if remaining >= 0:
                    msg += f" - Next averages expected in about {remaining} seconds"

        self.status_label.config(text=msg)
        self.root.after(1000, self._update_status_label)

    def _process_queue(self):
        avg_updated = False
        sensors_updated = False

        while True:
            try:
                event = self.ia.queue.get_nowait()
            except queue.Empty:
                break

            etype = event.get("type")

            if etype == "average":
                mt = event["measurement_type"]
                agent_id = event["agent_id"]
                value = event["value"]
                ts_str = self._format_timestamp(event["timestamp"])

                key = (mt, agent_id)
                if key in self.avg_items:
                    item_id = self.avg_items[key]
                    self.avg_tree.item(
                        item_id,
                        values=(mt, agent_id, value, ts_str),
                    )
                else:
                    item_id = self.avg_tree.insert(
                        "",
                        "end",
                        values=(mt, agent_id, value, ts_str),
                    )
                    self.avg_items[key] = item_id

                avg_updated = True
                if not self.has_avg_data:
                    self.has_avg_data = True
                self._reset_expected_time()

            elif etype == "sensor_value":
                sensor_id = event["sensor_id"]
                room = event["room"]
                mt = event["measurement_type"]
                value = event["value"]
                ts_str = self._format_timestamp(event["timestamp"])

                state = self._ensure_sensor_entry(sensor_id, room, mt)
                state["last_value"] = value
                state["last_event"] = ts_str
                self._update_sensor_row(sensor_id)
                sensors_updated = True


            elif etype == "alert":
                sensor_id = event["sensor_id"]
                room = event.get("room")
                mt = event.get("measurement_type")
                value = event.get("value")
                ts_str = self._format_timestamp(event["timestamp"])

                if sensor_id is None:
                    continue

                state = self._ensure_sensor_entry(sensor_id, room, mt)
                state["last_value"] = value
                state["status"] = "FAULTY"
                state["last_event"] = ts_str
                self._update_sensor_row(sensor_id)
                sensors_updated = True

            elif etype == "reset":
                sensor_id = event["sensor_id"]
                ts_str = self._format_timestamp(event["timestamp"])

                state = self._ensure_sensor_entry(sensor_id)
                state["status"] = "RESET_SENT"
                state["last_event"] = ts_str
                self._update_sensor_row(sensor_id)

                self.total_reset_sent += 1
                self._schedule_reset_clear(sensor_id)
                sensors_updated = True

        self.root.after(200, self._process_queue)


def main(num_sensors: int = 10, num_aa: int = 3):
    ia = InterfaceAgent(BROKER_HOST, BROKER_PORT, REFUGE_NAME)
    ia.connect()

    root = tk.Tk()
    gui = InterfaceGUI(root, ia, refresh_period_s=REFRESH_PERIOD_S,averages_height=num_aa,sensors_height=num_sensors)

    try:
        root.mainloop()
    finally:
        ia.stop()


if __name__ == "__main__":
    main()
