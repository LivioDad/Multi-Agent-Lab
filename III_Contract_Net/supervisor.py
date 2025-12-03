import argparse
import time
import threading
from collections import defaultdict

import paho.mqtt.client as mqtt
from common import (
    CfP, Accept, now_s, jload, new_job_id,
    t_cfp, t_proposals, t_accept, t_done
)

"""
Supervisor:
- Publishes CfP for each job type with a deadline.
- Collects proposals until the deadline.
- Picks the lowest ETA and sends Accept to that machine.
- Optionally waits for DONE.
"""

def main():
    ap = argparse.ArgumentParser(description="Contract Net Supervisor (MQTT)")
    ap.add_argument(
        "--jobs",
        default="cut,drill,cut,paint,drill",
        help="Comma-separated job types (e.g., cut,drill,paint)"
    )
    ap.add_argument(
        "--deadline",
        type=float,
        default=1.0,
        help="Seconds to wait for proposals per round"
    )
    ap.add_argument(
        "--wait-done",
        action="store_true",
        help="Wait for DONE before moving to the next job"
    )
    ap.add_argument("--broker", default="localhost", help="MQTT broker host")
    ap.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = ap.parse_args()

    job_types = [x.strip() for x in args.jobs.split(",") if x.strip()]

    client = mqtt.Client(client_id="supervisor", clean_session=True)

    proposals = defaultdict(list)    # job_id -> list of proposals
    done_events = {}                 # job_id -> threading.Event

    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            client.subscribe(t_proposals(), qos=0)
            client.subscribe(t_done(), qos=0)
            print("[SUP] Connected")
        else:
            print(f"[SUP] Connect failed rc={rc}")

    def on_proposal(_client, _userdata, msg):
        try:
            p = jload(msg.payload)
            jid = p["job_id"]
            proposals[jid].append(p)
            print(f"[SUP] Proposal: job={jid} type={p['job_type']} from={p['machine_id']} eta={p['eta_s']}s")
        except Exception as e:
            print(f"[SUP] on_proposal error: {e}")

    def on_done(_client, _userdata, msg):
        try:
            d = jload(msg.payload)
            jid = d["job_id"]
            elapsed = d["finished_at"] - d["started_at"]
            print(f"[SUP] DONE: job={jid} by={d['machine_id']} elapsed={elapsed:.2f}s")
            ev = done_events.get(jid)
            if ev:
                ev.set()
        except Exception as e:
            print(f"[SUP] on_done error: {e}")

    client.on_connect = on_connect
    client.message_callback_add(t_proposals(), on_proposal)
    client.message_callback_add(t_done(), on_done)
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    try:
        for jt in job_types:
            jid = new_job_id()
            proposals[jid].clear()
            done_events[jid] = threading.Event()

            # Send CfP for this job
            cfp = CfP(job_id=jid, job_type=jt, deadline_s=args.deadline, issued_at=now_s())
            client.publish(t_cfp(jt), cfp.to_msg(), qos=0)
            print(f"\n[SUP] CFP: job={jid} type={jt} deadline={args.deadline:.2f}s")

            # Wait for proposals until deadline
            t0 = now_s()
            while now_s() - t0 < args.deadline:
                time.sleep(0.02)

            ps = proposals[jid]
            if not ps:
                print(f"[SUP] No proposals for job={jid} (skipped)")
                continue

            # Pick lowest ETA
            win = min(ps, key=lambda p: float(p["eta_s"]))
            print(f"[SUP] WIN: job={jid} type={jt} -> {win['machine_id']} (eta={win['eta_s']}s)")

            # Send Accept to the winner only
            client.publish(t_accept(win["machine_id"]), Accept(jid, jt).to_msg(), qos=0)

            # Optionally wait for DONE
            if args.wait_done:
                done_events[jid].wait()
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
