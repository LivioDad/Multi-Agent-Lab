import argparse
import json
import threading
import time

import paho.mqtt.client as mqtt
from common import (
    Proposal, Done, now_s, jload,
    t_cfp, t_proposals, t_accept, t_done
)

"""
Machine agent:
- Listens for CfP by job_type.
- If free and capable, sends a Proposal with its ETA.
- When it receives an Accept addressed to this machine, it runs the job (becomes busy) and then publishes DONE.
"""

def parse_caps(caps_arg: str) -> dict:
    """
    Accepted formats:
      --caps "cut:3,drill:5,paint:2.5"
      --caps-json '{"cut":3,"drill":5}'
    """
    try:
        if caps_arg:
            caps = {}
            for kv in caps_arg.split(","):
                if not kv.strip():
                    continue
                k, v = kv.split(":")
                caps[k.strip()] = float(v.strip())
            return caps
    except Exception:
        pass
    return {}

def main():
    ap = argparse.ArgumentParser(description="Contract Net Machine (MQTT)")
    ap.add_argument("--machine-id", required=True, help="Unique machine identifier")
    ap.add_argument("--caps", default="", help='Capabilities like "cut:3,drill:5,paint:2.5" (seconds)')
    ap.add_argument("--caps-json", default="", help="Capabilities in JSON")
    ap.add_argument("--broker", default="localhost", help="MQTT broker host")
    ap.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = ap.parse_args()

    caps = parse_caps(args.caps)
    if (not caps) and args.caps_json:
        caps = json.loads(args.caps_json)

    if not caps:
        raise SystemExit("Define capabilities with --caps or --caps-json")

    busy_lock = threading.Lock()
    busy = {"flag": False, "job_id": None, "job_type": None}

    client = mqtt.Client(client_id=f"machine-{args.machine_id}", clean_session=True)

    def is_busy() -> bool:
        with busy_lock:
            return busy["flag"]

    def set_busy(val: bool, job_id=None, job_type=None):
        with busy_lock:
            busy["flag"] = val
            busy["job_id"] = job_id
            busy["job_type"] = job_type

    # CfP handler: decide whether to bid
    def on_cfp(client, _userdata, msg):
        if is_busy():
            return
        try:
            cfp = jload(msg.payload)
            job_type = cfp["job_type"]
            job_id = cfp["job_id"]
            if job_type not in caps:
                return
            eta = float(caps[job_type])
            prop = Proposal(
                job_id=job_id,
                job_type=job_type,
                machine_id=args.machine_id,
                eta_s=eta,
                at=now_s(),
            )
            client.publish(t_proposals(), prop.to_msg(), qos=0)
            print(f"[{args.machine_id}] Proposal -> job={job_id} type={job_type} eta={eta}s")
        except Exception as e:
            print(f"[{args.machine_id}] on_cfp error: {e}")

    # Accept handler: run only if addressed to this machine
    def on_accept(client, _userdata, msg):
        try:
            acc = jload(msg.payload)
            job_id = acc["job_id"]
            job_type = acc["job_type"]
            if is_busy():
                return

            set_busy(True, job_id, job_type)
            print(f"[{args.machine_id}] ACCEPTED -> job={job_id} type={job_type}, running...")

            def run_job():
                started = now_s()
                duration = float(caps[job_type])
                time.sleep(duration)  # simulate work
                finished = now_s()
                client.publish(
                    t_done(),
                    Done(job_id, job_type, args.machine_id, started, finished).to_msg(),
                    qos=0,
                )
                print(f"[{args.machine_id}] DONE -> job={job_id} ({duration}s)")
                set_busy(False, None, None)

            threading.Thread(target=run_job, daemon=True).start()
        except Exception as e:
            print(f"[{args.machine_id}] on_accept error: {e}")

    # Subscribe to CfP for supported types and to this machine's Accept topic
    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            for jt in caps.keys():
                client.subscribe(t_cfp(jt), qos=0)
            client.subscribe(t_accept(args.machine_id), qos=0)
            print(f"[{args.machine_id}] Connected. Caps={caps}")
        else:
            print(f"[{args.machine_id}] Connect failed rc={rc}")

    client.on_connect = on_connect
    client.message_callback_add("lab/cnp/cfp/+", on_cfp)
    client.message_callback_add(f"lab/cnp/accept/{args.machine_id}", on_accept)

    client.connect(args.broker, args.port, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
