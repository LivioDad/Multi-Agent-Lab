# Contract Net Protocol (MQTT) — Contract Part

This directory contains a implementation of the **Contract Net Protocol (CNP)** using **MQTT**:
a **Supervisor** publishes *Call for Proposals (CfP)*, **Machine** agents answer with *Proposals*, and the
Supervisor selects a winner and sends an *Accept*. The selected Machine executes the job and publishes *Done*.

---

## Components (clients)

### 1) `machine.py` — Machine Agent
A worker agent that:
- subscribes to CfP topics for the job types it supports,
- sends a Proposal with its ETA if it is free and capable,
- listens to its dedicated Accept topic,
- runs the job (simulated with `sleep`) and publishes Done

**Parameters**
- `--machine-id` *(required)*: unique identifier (e.g., `M1`, `M2`)
- `--caps` *(optional)*: capabilities as durations in seconds, format: `"cut:3,drill:5,paint:2.5"`
- `--caps-json` *(optional)*: same capabilities as JSON string (used if `--caps` not provided)
- `--broker` *(default: `localhost`)*: MQTT broker host
- `--port` *(default: `1883`)*: MQTT broker port

---

### 2) `supervisor.py` — Supervisor (baseline)
A coordinator agent that:
- publishes CfP for each job in a sequence,
- collects proposals for a fixed deadline,
- selects the lowest ETA proposal,
- sends Accept to the winner,
- optionally waits for Done before moving to the next job

**Parameters**
- `--jobs` *(default: `cut,drill,cut,paint,drill`)*: comma-separated list of job types
- `--deadline` *(default: `1.0`)*: proposal collection window (seconds) per job
- `--wait-done` *(flag)*: wait for Done before starting the next job
- `--broker` *(default: `localhost`)*, `--port` *(default: `1883`)* 

---

### 3) `supervisor_opt.py` — Supervisor (optimized)
An improved supervisor with:
- **early stopping** (stop bidding when enough bids arrive or after a “quiet” period),
- **lookahead guard** (if the next job is the same type, optionally choose the 2nd-best ETA if close, to keep the fastest machine available). 

**Parameters (baseline + optimizations)**
- All parameters from `supervisor.py`
- `--min-bids` *(default: `0`)*: early-stop when at least N unique machines proposed
- `--quiet-ms` *(default: `0`)*: early-stop if no new proposal is received for N milliseconds
- `--guard-fast` *(flag)*: enable lookahead guard for consecutive same-type jobs
- `--alpha` *(default: `1.15`)*: choose 2nd-best if `ETA2 <= alpha * ETA1` 

---

### 4) `common.py` — Shared protocol utilities
Shared message structures (CfP / Proposal / Accept / Done), JSON helpers, time utilities, and topic helpers
used by all clients. 

---

## MQTT Topics (protocol)
The scripts use a topic hierarchy like:
- CfP (per job type): `lab/cnp/cfp/<job_type>`
- Proposals (all): `lab/cnp/proposals`
- Accept (per machine): `lab/cnp/accept/<machine_id>`
- Done (all): `lab/cnp/done` 

---

## Typical Run (Windows)
1) Start your MQTT 
2) Run the run_all.bat file 

## Typical Run (Linux)
1) Start your MQTT 
2) Start multiple machines with different capabilities:
   - `python machine.py --machine-id M1 --caps "cut:2,drill:5,paint:1.5"`
   - `python machine.py --machine-id M2 --caps "cut:3.5,drill:2,paint:2"`
3) Start the supervisor:
   - Baseline: `python supervisor.py --jobs "cut,drill,cut,paint,drill" --deadline 1.0 --wait-done`
   - Optimized: `python supervisor_opt.py --jobs "cut,drill,cut,paint,drill" --deadline 1.0 --min-bids 2 --quiet-ms 200 --guard-fast --alpha 1.15` 
