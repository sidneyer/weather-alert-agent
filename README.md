# weather-alert-agent

A privacy-focused self-hosted weather intelligence agent using the public National Weather Service API.
Unlike typical weather apps, weather-alert-agent focuses on actionable local alerts, relevance filtering, and multi-channel notifications instead of generic forecasts.


## Features

- Real-time National Weather Service alert monitoring
- Self-hosted and outbound-only
- No cloud account required
- No telemetry
- No inbound ports required
- Matrix notifications
- Experimental ntfy support
- Experimental Discord webhook support
- Experimental Telegram support
- RSS feed generation
- Multi-location monitoring
- Quiet hours with critical alert override
- Marine and coastal alert relevance
- Commuter/outdoor relevance profiles
- Severity classification
- Recommended action summaries
- State-based alert deduplication
- launchd-friendly automation
- Interactive setup wizard
- Lightweight Python implementation

## Designed for

- Homelab users
- Self-hosters
- Privacy-conscious users
- Emergency preparedness
- Coastal communities
- Marine users
- Power users who want alert routing and filtering

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
