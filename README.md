# Multi-Agent Systems – MQTT Laboratory

## Overview
This repository contains the implementation of several laboratory exercises
focused on MQTT communication and multi-agent systems.

The project is structured as a set of independent exercises, each addressing
a specific aspect of distributed systems, agent coordination and communication.
Each exercise is located in its own directory and documented with a dedicated
README.md.

The global specifications of the laboratory are provided in MQTT_Lab.pdf.

## Repository Structure

.
├── I_MQTT_Basics/
├── II_Sensor_Network/
├── III_Contract_Net/
├── MQTT_Lab.pdf
└── README.md

## Exercises

I – MQTT Basics
Introduction to MQTT communication:
- basic publish / subscribe model
- simple MQTT clients
- topic-based message exchange

See I_MQTT_Basics/README.md

II – Sensor Network
Implementation of a MQTT-based sensor network using a multi-agent architecture.
Includes sensor agents, aggregation agents, dynamic behavior and anomaly detection.

See II_Sensor_Network/README.md

III – Contract Net
Implementation of a Contract Net Protocol with manager and contractor agents.

See III_Contract_Net/README.md

## Requirements
- Python 3
- MQTT broker (e.g. Mosquitto)
- paho-mqtt Python library

## Usage
Each exercise can be executed independently.
Refer to the README.md inside each directory for detailed instructions.

## Notes
This repository follows standard academic and software engineering practices
with clear separation between exercises and concise documentation.
