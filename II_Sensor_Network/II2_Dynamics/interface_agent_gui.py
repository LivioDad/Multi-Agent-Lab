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
    Interface Agent
    Subscribes to: {refuge_name}/AA/+/+
    Each message becomes (measurement_type, agent_id, value, timestamp) inside a queue
    The GUI consumes that queue in the Tk main thread
    """

    def __init__(self, broker_host: str, broker_port: int, refuge_name: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name

        self.topic_in = f"{refuge_name}/AA/+/+"

        self.client = mqtt.Client()
        self.queue: "queue.Queue[tuple[str, str, float, str]]" = queue.Queue()

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[IA] Connected to MQTT broker ({status}). Subscribing to: {self.topic_in}")
        client.subscribe(self.topic_in)

    def _on_message(self, client, userdata, msg):
        try:
            value = float(msg.payload.decode())
        except ValueError:
            print(f"[IA] Skipping non numeric payload on {msg.topic}: {msg.payload!r}")
            return

        try:
            _, _, measurement_type, agent_id = msg.topic.split("/")
        except ValueError:
            print(f"[IA] Unexpected topic format: {msg.topic}")
            return

        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.queue.put((measurement_type, agent_id, value, timestamp))

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
    Tkinter GUI showing:
    measurement_type | agent_id | last_average | timestamp
    Plus a simple waiting message that disappears when data starts arriving
    """

    def __init__(self, root: tk.Tk, ia: InterfaceAgent, refresh_period_s: int = REFRESH_PERIOD_S, table_height: int = 5):
        self.root = root
        self.ia = ia

        self.root.title("Refuge averages")

        # Waiting label shown before receiving first data
        self.status_label = ttk.Label(
            root,
            text="Waiting for incoming data...",
            anchor="center"
        )
        self.status_label.pack(fill="x", padx=10, pady=(10, 0))

        # Table
        columns = ("measurement_type", "agent_id", "value", "timestamp")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=table_height)
        self.tree.heading("measurement_type", text="Measurement type")
        self.tree.heading("agent_id", text="Agent")
        self.tree.heading("value", text="Last average")
        self.tree.heading("timestamp", text="Arrival time")

        self.tree.column("measurement_type", width=150, anchor="center")
        self.tree.column("agent_id", width=80, anchor="center")
        self.tree.column("value", width=100, anchor="center")
        self.tree.column("timestamp", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree_items: dict[tuple[str, str], str] = {}
        self.received_any_data = False  # used to hide waiting message

        self.root.after(200, self._process_queue)

    def _process_queue(self):
        """
        Processes all messages from the queue and updates the GUI.
        Hides the waiting label when the first data arrives.
        """

        updated = False

        while True:
            try:
                measurement_type, agent_id, value, timestamp = self.ia.queue.get_nowait()
            except queue.Empty:
                break

            updated = True

            if not self.received_any_data:
                self.received_any_data = True
                self.status_label.pack_forget()

            key = (measurement_type, agent_id)

            if key in self.tree_items:
                item_id = self.tree_items[key]
                self.tree.item(item_id, values=(measurement_type, agent_id, value, timestamp))
            else:
                item_id = self.tree.insert("", "end", values=(measurement_type, agent_id, value, timestamp))
                self.tree_items[key] = item_id

        self.root.after(200, self._process_queue)


def main(num_aa: int = 3):
    ia = InterfaceAgent(BROKER_HOST, BROKER_PORT, REFUGE_NAME)
    ia.connect()

    root = tk.Tk()
    gui = InterfaceGUI(root, ia, refresh_period_s=REFRESH_PERIOD_S, table_height=num_aa)

    try:
        root.mainloop()
    finally:
        ia.stop()


if __name__ == "__main__":
    main()
