# weather-alert-agent

A small self-hosted weather alert agent using the public National Weather Service API.

It checks for active weather alerts for a configured latitude/longitude, deduplicates alerts, and sends notifications.

## Features

- National Weather Service alert polling
- State-based deduplication
- Matrix notifications
- Experimental ntfy notifications
- RSS feed output
- stdout logging
- launchd-friendly
- No inbound network exposure required

## Requirements

- Python 3
- requests
- pyyaml

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[200~```

## Configuration

Copy the example config:

```bash
cp config.example.yaml config.yaml
```

Edit:

```bash
nano config.yaml
```

## Run

```bash
./weather_alert_agent.py
```

## Test

```bash
./weather_alert_agent.py --test
```

## Automation

Runs well with launchd every 120 seconds.

## Disclaimer

Unofficial project. Not affiliated with NOAA or the National Weather Service.

## Setup Wizard

Before running setup, have this ready:

Required:
- Location name
- Latitude
- Longitude

Optional:
- Matrix homeserver
- Matrix room ID
- Matrix access token
- ntfy topic/token
- Discord webhook URL
- Telegram bot token/chat ID
- RSS output path

Run:

```bash
python3 setup.py
