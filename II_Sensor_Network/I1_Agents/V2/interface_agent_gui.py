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

# Expected period in seconds between new averages published by AveragingAgents
REFRESH_PERIOD_S = config["TW_AA"]


class InterfaceAgent:
    """
    Interface Agent
    - subscribes to: {refuge_name}/AA/+/+ (e.g., refuge_Monviso/AA/temperature/AA1)
    - for each message received, puts (measurement_type, agent_id, value, timestamp) into a queue
      The GUI reads from this queue in the Tk main thread
    """

    def __init__(self, broker_host: str, broker_port: int, refuge_name: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name

        self.topic_in = f"{refuge_name}/AA/+/+"

        self.client = mqtt.Client()
        # Queue is thread safe; producer is the MQTT thread, consumer is the Tk main thread
        self.queue: "queue.Queue[tuple[str, str, float, str]]" = queue.Queue()

    # MQTT callbacks 
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

        # Expected topic format: refuge_Monviso/AA/<measurement_type>/<agent_id>
        try:
            _, _, measurement_type, agent_id = msg.topic.split("/")
        except ValueError:
            print(f"[IA] Unexpected topic format: {msg.topic}")
            return

        # Format arrival time as local time HH:MM:SS
        arrival_time_str = time.strftime("%H:%M:%S", time.localtime())

        # Push data to the queue for the GUI
        self.queue.put((measurement_type, agent_id, value, arrival_time_str))


    # Public API
    def connect(self) -> None:
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        # Run MQTT network loop in a background thread
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        print("[IA] stopped successfully")


class InterfaceGUI:
    """
    Tkinter GUI showing a table:
        measurement_type | agent_id | last_average | timestamp
    plus a countdown label for the next expected update
    """

    def __init__(self, root: tk.Tk, ia: InterfaceAgent, refresh_period_s: int = REFRESH_PERIOD_S, table_height: int = 5):
        self.root = root
        self.ia = ia
        self.refresh_period_s = refresh_period_s

        self.root.title("Refuge averages")

        # Use monotonic time for reliable countdown (immune to system clock jumps)
        self._now = time.monotonic
        self.next_expected_time = self._now() + self.refresh_period_s

        # Top status label (countdown)
        self.status_label = ttk.Label(
            root,
            text="Waiting for first data...",
            anchor="center",
        )
        self.status_label.pack(fill="x", padx=10, pady=(10, 0))

        #  Table
        columns = ("measurement_type", "agent_id", "value", "timestamp")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=table_height)
        self.tree.heading("measurement_type", text="Measurement type")
        self.tree.heading("agent_id", text="Agent")
        self.tree.heading("value", text="Last average")
        self.tree.heading("timestamp", text="Arrival time")

        # Basic fixed widths
        self.tree.column("measurement_type", width=150, anchor="center")
        self.tree.column("agent_id", width=80, anchor="center")
        self.tree.column("value", width=100, anchor="center")
        self.tree.column("timestamp", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Map (measurement_type, agent_id) to Treeview item id
        self.tree_items: dict[tuple[str, str], str] = {}

        # Start periodic tasks
        self.root.after(200, self._process_queue)
        self.root.after(200, self._update_status_label)

    # Helpers

    def _reset_expected_time(self):
        """Restart the countdown from now plus refresh_period_s."""
        self.next_expected_time = self._now() + self.refresh_period_s

    def _update_status_label(self):
        """
        Update the countdown text based on the difference between now
        and the next_expected_time. This is time based, not simple counter based,
        so it stays reliable even if Tk after callbacks are a bit late
        """
        now = self._now()
        delta = self.next_expected_time - now
        remaining = int(round(delta))

        if remaining >= 0:
            msg = f"Next data expected in {remaining} s"
        else:
            # Data is late compared to expected period
            msg = f"Waiting for new data... ({-remaining} s late)"

        self.status_label.config(text=msg)

        # Schedule the next countdown update
        self.root.after(500, self._update_status_label)

    def _process_queue(self):
        """
        Read all pending messages from the queue and update or create rows
        in the table. Keep this function very fast and non blocking so it
        never freezes the Tk mainloop
        """
        updated = False

        while True:
            try:
                measurement_type, agent_id, value, timestamp = self.ia.queue.get_nowait()
            except queue.Empty:
                break

            updated = True
            key = (measurement_type, agent_id)
            if key in self.tree_items:
                item_id = self.tree_items[key]
                self.tree.item(
                    item_id,
                    values=(measurement_type, agent_id, value, timestamp),
                )
            else:
                item_id = self.tree.insert(
                    "",
                    "end",
                    values=(measurement_type, agent_id, value, timestamp),
                )
                self.tree_items[key] = item_id

        if updated:
            # New data received so reset countdown
            self._reset_expected_time()

        # Schedule next poll of the queue
        self.root.after(200, self._process_queue)


def main(num_aa: int = 3):
    # Create and start InterfaceAgent (MQTT)
    ia = InterfaceAgent(BROKER_HOST, BROKER_PORT, REFUGE_NAME)
    ia.connect()

    # Create the GUI
    root = tk.Tk()
    gui = InterfaceGUI(root, ia, refresh_period_s=REFRESH_PERIOD_S,table_height=num_aa)

    try:
        root.mainloop()
    finally:
        ia.stop()


if __name__ == "__main__":
    main()
