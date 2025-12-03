import argparse, time, threading
from collections import defaultdict
import paho.mqtt.client as mqtt
from common import CfP, Accept, now_s, jload, new_job_id, t_cfp, t_proposals, t_accept, t_done

"""
Optimized Supervisor:
- Early stop: end bidding when min bids reached or after a quiet period.
- Lookahead (n=1): if next job has same type, optionally keep the fastest free by picking second-best
  when it's close enough (factor alpha).
- Dedicated topics are already used via t_cfp(job_type).
"""

def main():
    ap = argparse.ArgumentParser(description="Contract Net Supervisor (optimized)")
    ap.add_argument("--jobs", default="cut,drill,cut,paint,drill", help="Comma-separated job types")
    ap.add_argument("--deadline", type=float, default=1.0, help="Max seconds to wait per round")
    ap.add_argument("--wait-done", action="store_true", help="Wait for DONE before next job")

    # Optimizations
    ap.add_argument("--min-bids", type=int, default=0, help="Early-stop when at least this many proposals arrive")
    ap.add_argument("--quiet-ms", type=int, default=0, help="Early-stop if no new proposals for this many ms")
    ap.add_argument("--guard-fast", action="store_true",
                    help="If next job has same type, prefer 2nd-best when close enough")
    ap.add_argument("--alpha", type=float, default=1.15,
                    help="Second-best ETA must be <= alpha * best ETA to be chosen (with --guard-fast)")

    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    args = ap.parse_args()

    job_types = [x.strip() for x in args.jobs.split(",") if x.strip()]
    client = mqtt.Client(client_id="supervisor_opt", clean_session=True)

    proposals = defaultdict(list)  # job_id -> list[proposal]
    last_rx = {}                   # job_id -> last proposal time (seconds)
    done_events = {}               # job_id -> Event

    def on_connect(client, _u, _f, rc):
        if rc == 0:
            client.subscribe(t_proposals(), qos=0)
            client.subscribe(t_done(), qos=0)
            print("[SUP+] Connected")
        else:
            print(f"[SUP+] Connect failed rc={rc}")

    def on_proposal(_c, _u, msg):
        try:
            p = jload(msg.payload)
            jid = p["job_id"]
            proposals[jid].append(p)
            last_rx[jid] = now_s()
            print(f"[SUP+] Proposal: job={jid} type={p['job_type']} from={p['machine_id']} eta={p['eta_s']}s")
        except Exception as e:
            print(f"[SUP+] on_proposal error: {e}")

    def on_done(_c, _u, msg):
        try:
            d = jload(msg.payload)
            jid = d["job_id"]
            elapsed = d["finished_at"] - d["started_at"]
            print(f"[SUP+] DONE: job={jid} by={d['machine_id']} elapsed={elapsed:.2f}s")
            ev = done_events.get(jid)
            if ev: ev.set()
        except Exception as e:
            print(f"[SUP+] on_done error: {e}")

    client.on_connect = on_connect
    client.message_callback_add(t_proposals(), on_proposal)
    client.message_callback_add(t_done(), on_done)
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    try:
        for idx, jt in enumerate(job_types):
            jid = new_job_id()
            proposals[jid].clear()
            done_events[jid] = threading.Event()
            last_rx[jid] = now_s()

            cfp = CfP(job_id=jid, job_type=jt, deadline_s=args.deadline, issued_at=now_s())
            client.publish(t_cfp(jt), cfp.to_msg(), qos=0)
            print(f"\n[SUP+] CFP: job={jid} type={jt} deadline={args.deadline:.2f}s")

            # Wait for proposals with early-stop conditions
            t0 = now_s()
            while True:
                elapsed = now_s() - t0
                if elapsed >= args.deadline:
                    break
                # early stop: min bids reached?
                if args.min_bids > 0:
                    uniq = {p["machine_id"] for p in proposals[jid]}
                    if len(uniq) >= args.min_bids:
                        break
                # early stop: quiet period?
                if args.quiet_ms > 0:
                    if (now_s() - last_rx[jid]) * 1000.0 >= args.quiet_ms:
                        break
                time.sleep(0.02)

            ps = proposals[jid]
            if not ps:
                print(f"[SUP+] No proposals for job={jid} (skipped)")
                continue

            # Sort by ETA (ascending)
            ps_sorted = sorted(ps, key=lambda p: float(p["eta_s"]))
            winner = ps_sorted[0]

            # Light lookahead: keep fastest free if next job is the same type
            same_next = (idx + 1 < len(job_types) and job_types[idx + 1] == jt)
            if args.guard_fast and same_next and len(ps_sorted) >= 2:
                best_eta = float(ps_sorted[0]["eta_s"])
                second_eta = float(ps_sorted[1]["eta_s"])
                if second_eta <= args.alpha * best_eta:
                    winner = ps_sorted[1]
                    print(f"[SUP+] GUARD-FAST: picked 2nd best to keep fastest free "
                          f"(best={best_eta}s, second={second_eta}s, alpha={args.alpha})")

            print(f"[SUP+] WIN: job={jid} type={jt} -> {winner['machine_id']} (eta={winner['eta_s']}s)")
            client.publish(t_accept(winner["machine_id"]), Accept(jid, jt).to_msg(), qos=0)

            if args.wait_done:
                done_events[jid].wait()

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
