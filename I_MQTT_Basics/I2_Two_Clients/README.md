# I.2 – Two Clients

## Objective
Running multiple MQTT clients by implementing a simple **ping/pong** message exchange.
Two agents communicate through MQTT topics: when one receives the other’s keyword, it answers back.
This exercise also introduces an automated way to start several clients.

### Agent1.py (Pong agent)
`Agent1.py` implements the **pong** role:
- connects to the broker (`localhost:1883`)
- subscribes to its inbox topic
- sends an initial **kick** message (`ping`) to start the exchange
- whenever it receives `pong`, it waits `SLEEP` seconds and publishes `ping` on the outbox topic

### Agent2.py (Ping agent)
`Agent2.py` implements the **ping** role:
- connects to the broker (`localhost:1883`)
- subscribes to its inbox topic
- whenever it receives `ping`, it waits `SLEEP` seconds and publishes `pong` on the outbox topic

### Topics design
This implementation uses **two topics** to avoid reading back your own messages:
- Ping subscribes to `topic1` and publishes to `topic2`
- Pong subscribes to `topic2` and publishes to `topic1`

### master.bat
`master.bat` is provided to automatically start both agents without manually opening multiple terminals.

## Parameters
The agents can be configured by editing the constants in the scripts:
- `BROKER`: broker hostname/IP (default: `localhost`)
- `SLEEP`: delay before replying (seconds)
- `topic1` / `topic2`: communication topics (hard-coded in the scripts)

## How to run 
1. (Optional) Create and activate a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install paho-mqtt
   ```
2. Start the MQTT broker (e.g. shiftr.io Desktop)
3. On Windows run ```master.bat```
   On Linux/macOS run ```chmod +x master.sh``` and then ```./master.sh```
