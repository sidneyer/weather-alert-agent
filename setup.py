#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
CONFIG = PROJECT / "config.yaml"
ENV_FILE = PROJECT / ".env"


def ask(prompt, default=None, secret=False):
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default or ""


def yesno(prompt, default=False):
    d = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{d}]: ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes")


def write_file(path, text):
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    print("""
weather-alert-agent setup

Have this ready before continuing:

Required:
- Location name
- Latitude
- Longitude

Optional notifier details:
- Matrix homeserver, room ID, access token
- ntfy server/topic/token
- Discord webhook URL
- Telegram bot token and chat ID

Notes:
- Matrix room IDs usually start with !
- Tokens are written to .env, not config.yaml
- config.yaml is ignored by git
""")

    if CONFIG.exists() and not yesno("config.yaml already exists. Overwrite it?", False):
        print("Cancelled.")
        return

    location_name = ask("Location name", "Virginia Beach, VA")
    latitude = ask("Latitude", "36.8529")
    longitude = ask("Longitude", "-75.9780")

    commuter = yesno("Enable commuter relevance profile?", True)
    marine = yesno("Enable marine relevance profile?", True)
    outdoor = yesno("Enable outdoor relevance profile?", True)
    coastal = yesno("Enable coastal flooding relevance profile?", True)

    quiet = yesno("Enable quiet hours?", False)
    quiet_start = ask("Quiet hours start", "22:00") if quiet else "22:00"
    quiet_end = ask("Quiet hours end", "06:00") if quiet else "06:00"

    env_lines = []

    stdout_enabled = yesno("Enable stdout logging?", True)

    matrix_enabled = yesno("Enable Matrix notifications?", False)
    matrix_homeserver = "https://matrix.example.com"
    matrix_room = "!roomid:example.com"
    if matrix_enabled:
        matrix_homeserver = ask("Matrix homeserver", "https://matrix.example.com")
        matrix_room = ask("Matrix room ID")
        matrix_token = ask("Matrix access token")
        env_lines.append(f'MATRIX_ACCESS_TOKEN="{matrix_token}"')

    ntfy_enabled = yesno("Enable ntfy notifications?", False)
    ntfy_server = "https://ntfy.sh"
    ntfy_topic = ""
    if ntfy_enabled:
        ntfy_server = ask("ntfy server", "https://ntfy.sh")
        ntfy_topic = ask("ntfy topic")
        ntfy_token = ask("ntfy token, optional", "")
        env_lines.append(f'NTFY_TOPIC="{ntfy_topic}"')
        if ntfy_token:
            env_lines.append(f'NTFY_TOKEN="{ntfy_token}"')

    discord_enabled = yesno("Enable Discord webhook notifications?", False)
    if discord_enabled:
        webhook = ask("Discord webhook URL")
        env_lines.append(f'DISCORD_WEBHOOK_URL="{webhook}"')

    telegram_enabled = yesno("Enable Telegram notifications?", False)
    telegram_chat_id = ""
    if telegram_enabled:
        bot_token = ask("Telegram bot token")
        telegram_chat_id = ask("Telegram chat ID")
        env_lines.append(f'TELEGRAM_BOT_TOKEN="{bot_token}"')
        env_lines.append(f'TELEGRAM_CHAT_ID="{telegram_chat_id}"')

    rss_enabled = yesno("Enable local RSS output?", True)
    rss_output = ask("RSS output path", "./weather-alerts.xml") if rss_enabled else "./weather-alerts.xml"
    rss_title = ask("RSS title", f"{location_name} Weather Alerts") if rss_enabled else "Local Weather Alerts"
    rss_link = ask("RSS public/self link", "https://example.com/weather-alerts.xml") if rss_enabled else "https://example.com/weather-alerts.xml"

    config = f'''location:
  name: "{location_name}"
  latitude: {latitude}
  longitude: {longitude}

alerts:
  include: []
  exclude: []

profiles:
  commuter: {str(commuter).lower()}
  marine: {str(marine).lower()}
  outdoor: {str(outdoor).lower()}
  coastal_flooding: {str(coastal).lower()}

quiet_hours:
  enabled: {str(quiet).lower()}
  start: "{quiet_start}"
  end: "{quiet_end}"
  allow:
    - Tornado Warning
    - Flash Flood Warning
    - Hurricane Warning
    - Storm Surge Warning

notifications:
  stdout:
    enabled: {str(stdout_enabled).lower()}

  matrix:
    enabled: {str(matrix_enabled).lower()}
    homeserver: "{matrix_homeserver}"
    room_id: "{matrix_room}"
    access_token_env: "MATRIX_ACCESS_TOKEN"

  ntfy:
    enabled: {str(ntfy_enabled).lower()}
    server: "{ntfy_server}"
    topic: "{ntfy_topic}"
    topic_env: "NTFY_TOPIC"
    token_env: "NTFY_TOKEN"
    priority: 4
    tags: "warning,weather"

  discord:
    enabled: {str(discord_enabled).lower()}
    webhook_url_env: "DISCORD_WEBHOOK_URL"

  telegram:
    enabled: {str(telegram_enabled).lower()}
    bot_token_env: "TELEGRAM_BOT_TOKEN"
    chat_id: "{telegram_chat_id}"
    chat_id_env: "TELEGRAM_CHAT_ID"

rss:
  enabled: {str(rss_enabled).lower()}
  output_path: "{rss_output}"
  title: "{rss_title}"
  link: "{rss_link}"
  description: "Local NWS weather alerts"
  max_items: 50
'''

    write_file(CONFIG, config)

    if env_lines:
        write_file(ENV_FILE, "\n".join(env_lines) + "\n")
        print("Secrets written to .env")
    else:
        print("No .env secrets needed.")

    if yesno("Create virtual environment and install dependencies?", True):
        if not (PROJECT / ".venv").exists():
            run(["python3", "-m", "venv", str(PROJECT / ".venv")])
        run([str(PROJECT / ".venv/bin/pip"), "install", "-r", str(PROJECT / "requirements.txt")])

    print("""
Setup complete.

To test:

  cd "{project}"
  set -a; source .env 2>/dev/null; set +a
  ./.venv/bin/python weather_alert_agent.py --test

To run normally:

  set -a; source .env 2>/dev/null; set +a
  ./.venv/bin/python weather_alert_agent.py
""".format(project=PROJECT))


if __name__ == "__main__":
    main()
