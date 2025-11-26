import queue
import time
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

import paho.mqtt.client as mqtt


BROKER_HOST = "localhost"
BROKER_PORT = 1883
REFUGE_NAME = "refuge_Monviso"

# Expected period (in seconds) between new averages published by AveragingAgents.
# Keep it consistent with TW_AA in your config.json.
REFRESH_PERIOD_S = 10


class InterfaceAgent:
    """
    Interface Agent
    - subscribes to: {refuge_name}/AA/+/+ (e.g., refuge_Monviso/AA/temperature/AA1)
    - for each message received, puts (measurement_type, agent_id, value, timestamp)
      into a Queue. The GUI reads from this queue in the Tk main thread.
    """

    def __init__(self, broker_host: str, broker_port: int, refuge_name: str):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.refuge_name = refuge_name

        self.topic_in = f"{refuge_name}/AA/+/+"

        self.client = mqtt.Client()
        # Queue is thread-safe; producer = MQTT thread, consumer = Tk main thread
        self.queue: "queue.Queue[tuple[str, str, float, float]]" = queue.Queue()

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"ERROR rc={rc}"
        print(f"[IA] Connected to MQTT broker ({status}). Subscribing to: {self.topic_in}")
        client.subscribe(self.topic_in)

    def _on_message(self, client, userdata, msg):
        try:
            value = float(msg.payload.decode())
        except ValueError:
            print(f"[IA] Skipping non-numeric payload on {msg.topic}: {msg.payload!r}")
            return

        # Expected topic format: refuge_Monviso/AA/<measurement_type>/<agent_id>
        try:
            _, _, measurement_type, agent_id = msg.topic.split("/")
        except ValueError:
            print(f"[IA] Unexpected topic format: {msg.topic}")
            return

        # Current timestamp (seconds since epoch)
        ts = time.time()

        # Push data (including timestamp) to the queue for the GUI
        self.queue.put((measurement_type, agent_id, value, ts))

    # ---------- Public API ----------

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
    plus a status label (waiting / countdown for next expected update).
    """

    def __init__(self, root: tk.Tk, ia: InterfaceAgent, refresh_period_s: int = REFRESH_PERIOD_S):
        self.root = root
        self.ia = ia
        self.refresh_period_s = refresh_period_s

        self.root.title("Refuge averages")

        # Flag to know if we have already received at least one value
        self.has_data = False
        # Next expected time for new data (set after first data arrives)
        self.next_expected_time: float | None = None

        # ---- Table ----
        columns = ("measurement_type", "agent_id", "value", "timestamp")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        self.tree.heading("measurement_type", text="Measurement type")
        self.tree.heading("agent_id", text="Agent")
        self.tree.heading("value", text="Last average")
        self.tree.heading("timestamp", text="Timestamp")

        # Initial widths; will be adjusted dynamically to fit content
        self.tree.column("measurement_type", width=150, anchor="center")
        self.tree.column("agent_id", width=80, anchor="center")
        self.tree.column("value", width=100, anchor="center")
        self.tree.column("timestamp", width=160, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Status label under the table
        self.status_label = ttk.Label(root, text="Waiting for data (no averages yet)")
        self.status_label.pack(pady=(0, 10))

        # Map (measurement_type, agent_id) -> Treeview item id
        self.tree_items: dict[tuple[str, str], str] = {}

        # Font used to measure string width inside the Treeview
        try:
            # Try the Treeview-specific font if set
            tree_font_name = self.tree.cget("font")
            if tree_font_name:
                self.font = tkfont.nametofont(tree_font_name)
            else:
                self.font = tkfont.nametofont("TkDefaultFont")
        except tk.TclError:
            self.font = tkfont.nametofont("TkDefaultFont")

        # Start periodic tasks
        self.root.after(200, self._process_queue)
        self.root.after(200, self._update_status_label)

    # ---------- Internal helpers ----------

    def _now(self) -> float:
        """Return current time in seconds since epoch."""
        return time.time()

    def _reset_expected_time(self):
        """Restart the countdown from now + refresh_period_s."""
        self.next_expected_time = self._now() + self.refresh_period_s

    def _update_status_label(self):
        """
        Update the status text.
        - Before any data arrives: 'Waiting for data (no averages yet)'.
        - After first data: countdown until the next expected value.
        """
        if not self.has_data or self.next_expected_time is None:
            msg = "Waiting for data (no averages yet)"
        else:
            msg = "";

        self.status_label.config(text=msg)

        # Schedule the next status update
        self.root.after(500, self._update_status_label)

    def _adjust_column_widths(self):
        """
        Dynamically resize the columns so that content is fully visible.
        Called only when new data arrives to avoid unnecessary work.
        """
        for col in self.tree["columns"]:
            header_text = self.tree.heading(col, "text")
            max_width = self.font.measure(header_text)

            for item_id in self.tree.get_children(""):
                cell_text = str(self.tree.set(item_id, col))
                width = self.font.measure(cell_text)
                if width > max_width:
                    max_width = width

            # Add some padding
            self.tree.column(col, width=max_width + 20)

    def _format_timestamp(self, ts: float) -> str:
        """Convert a POSIX timestamp into a human-readable string."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    def _process_queue(self):
        """
        Read all pending messages from the queue and update/create rows
        in the table. Keep this function very fast and non-blocking so it
        never freezes the Tk mainloop.
        """
        updated = False

        while True:
            try:
                measurement_type, agent_id, value, ts = self.ia.queue.get_nowait()
            except queue.Empty:
                break

            updated = True
            key = (measurement_type, agent_id)
            ts_str = self._format_timestamp(ts)

            if key in self.tree_items:
                item_id = self.tree_items[key]
                self.tree.item(
                    item_id,
                    values=(measurement_type, agent_id, value, ts_str),
                )
            else:
                item_id = self.tree.insert(
                    "",
                    "end",
                    values=(measurement_type, agent_id, value, ts_str),
                )
                self.tree_items[key] = item_id

        if updated:
            # We have received at least one data point
            if not self.has_data:
                self.has_data = True
            # New data received → reset countdown and adjust columns
            self._reset_expected_time()
            self._adjust_column_widths()

        # Schedule next poll of the queue
        self.root.after(200, self._process_queue)


def main():
    # Create and start InterfaceAgent (MQTT)
    ia = InterfaceAgent(BROKER_HOST, BROKER_PORT, REFUGE_NAME)
    ia.connect()

    # Create the GUI
    root = tk.Tk()
    gui = InterfaceGUI(root, ia, refresh_period_s=REFRESH_PERIOD_S)

    try:
        root.mainloop()
    finally:
        ia.stop()


if __name__ == "__main__":
    main()
