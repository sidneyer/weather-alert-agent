#!/usr/bin/env python3
import json
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone, time as dtime
from urllib.parse import quote
from xml.sax.saxutils import escape

import requests
import yaml

CONFIG_FILE = Path("config.yaml")
STATE_FILE = Path("state.json")
USER_AGENT = "weather-alert-agent/0.2"

EVENT_LEVELS = {
    "Tornado Warning": "CRITICAL",
    "Flash Flood Warning": "CRITICAL",
    "Hurricane Warning": "CRITICAL",
    "Storm Surge Warning": "CRITICAL",
    "Severe Thunderstorm Warning": "HIGH",
    "Tropical Storm Warning": "HIGH",
    "Coastal Flood Warning": "HIGH",
    "Gale Warning": "HIGH",
    "High Wind Warning": "HIGH",
    "Small Craft Advisory": "MEDIUM",
    "Coastal Flood Advisory": "MEDIUM",
    "Flood Advisory": "MEDIUM",
    "Wind Advisory": "MEDIUM",
    "Special Weather Statement": "LOW",
}

ACTIONS = {
    "Tornado Warning": "Take shelter immediately in an interior room on the lowest floor.",
    "Flash Flood Warning": "Avoid travel. Never drive through flooded roads.",
    "Severe Thunderstorm Warning": "Move indoors and stay away from windows.",
    "Hurricane Warning": "Follow official evacuation or shelter guidance.",
    "Tropical Storm Warning": "Secure loose outdoor items and avoid unnecessary travel.",
    "Coastal Flood Warning": "Avoid low-lying roads and flood-prone areas.",
    "Coastal Flood Advisory": "Watch for nuisance flooding in low-lying areas.",
    "Small Craft Advisory": "Use caution on the water. Small craft conditions may be hazardous.",
    "Gale Warning": "Avoid marine travel unless properly equipped.",
    "High Wind Warning": "Secure outdoor items and avoid exposed areas.",
    "Wind Advisory": "Use caution driving high-profile vehicles.",
}

PROFILE_KEYWORDS = {
    "commuter": ["Flood", "Ice", "Snow", "Wind", "Thunderstorm", "Tornado", "Fog"],
    "marine": ["Small Craft", "Gale", "Marine", "Seas", "Surf", "Rip Current"],
    "outdoor": ["Thunderstorm", "Tornado", "Heat", "Cold", "Wind", "Lightning"],
    "coastal_flooding": ["Coastal Flood", "Storm Surge", "High Surf", "Rip Current"],
}


def load_config():
    return yaml.safe_load(CONFIG_FILE.read_text())


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_alerts": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def nws_get(url):
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    return nws_get(url).get("features", [])


def iter_locations(config):
    if config.get("locations"):
        return config["locations"]
    return [config["location"]]


def event_level(config, event):
    custom = config.get("severity_map", {}) or {}
    return custom.get(event) or EVENT_LEVELS.get(event, "INFO")


def action_for_event(event):
    return ACTIONS.get(event, "Review the official alert and follow local guidance.")


def active_profiles(config, event):
    active = []
    for profile, enabled in (config.get("profiles", {}) or {}).items():
        if not enabled:
            continue
        if any(k.lower() in event.lower() for k in PROFILE_KEYWORDS.get(profile, [])):
            active.append(profile)
    return active


def quiet_hours_active(config, event):
    qh = config.get("quiet_hours", {}) or {}
    if not qh.get("enabled"):
        return False

    if event in set(qh.get("allow", []) or []):
        return False

    start = dtime.fromisoformat(qh.get("start", "22:00"))
    end = dtime.fromisoformat(qh.get("end", "06:00"))
    now = datetime.now().time()

    if start < end:
        return start <= now <= end
    return now >= start or now <= end


def should_include_event(config, event):
    alerts = config.get("alerts", {}) or {}
    include = set(alerts.get("include", []) or [])
    exclude = set(alerts.get("exclude", []) or [])

    if event in exclude:
        return False
    if include and event not in include:
        return False
    return True


def format_alert(config, feature, location_name):
    props = feature.get("properties", {})

    event = props.get("event", "Weather Alert")
    headline = props.get("headline") or event
    nws_severity = props.get("severity", "Unknown")
    area = props.get("areaDesc", "Unknown area")
    expires = props.get("expires", "")
    description = (props.get("description") or "").strip().replace("\n", " ")
    instruction = (props.get("instruction") or "").strip()
    url = props.get("@id") or props.get("id") or ""

    level = event_level(config, event)
    profiles = active_profiles(config, event)
    action = instruction or action_for_event(event)

    if len(description) > 650:
        description = description[:650].rsplit(" ", 1)[0] + "..."

    icon = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🔶", "LOW": "ℹ️", "INFO": "ℹ️"}.get(level, "ℹ️")

    lines = [
        f"{icon} {level}: {event}",
        "",
        headline,
        "",
        f"Location: {location_name}",
        f"Area: {area}",
        f"NWS severity: {nws_severity}",
        f"Expires: {expires}",
    ]

    if profiles:
        lines += ["", f"Relevant profiles: {', '.join(profiles)}"]

    if description:
        lines += ["", "Summary:", description]

    if action:
        lines += ["", "Recommended action:", action]

    if url:
        lines += ["", f"Official source: {url}"]

    return "\n".join(lines)


def send_matrix(config, message):
    matrix = config.get("notifications", {}).get("matrix", {})
    if not matrix.get("enabled"):
        return

    token = os.environ.get(matrix.get("access_token_env", "MATRIX_ACCESS_TOKEN"))
    if not token:
        raise RuntimeError("Matrix token env var is not set")

    homeserver = matrix["homeserver"].rstrip("/")
    room_id = matrix["room_id"]
    url = f"{homeserver}/_matrix/client/v3/rooms/{quote(room_id, safe='')}/send/m.room.message/{uuid.uuid4()}"

    r = requests.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"msgtype": "m.text", "body": message},
        timeout=30,
    )
    r.raise_for_status()


def send_ntfy(config, message):
    ntfy = config.get("notifications", {}).get("ntfy", {})
    if not ntfy.get("enabled"):
        return

    server = ntfy.get("server", "https://ntfy.sh").rstrip("/")
    topic = ntfy.get("topic") or os.environ.get(ntfy.get("topic_env", "NTFY_TOPIC"))
    token = os.environ.get(ntfy.get("token_env", "NTFY_TOKEN"))

    if not topic:
        raise RuntimeError("ntfy topic is not set")

    headers = {
        "Title": "Weather Alert",
        "Priority": str(ntfy.get("priority", 4)),
        "Tags": ntfy.get("tags", "warning,weather"),
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.post(f"{server}/{topic}", data=message.encode("utf-8"), headers=headers, timeout=30)
    r.raise_for_status()


def send_discord(config, message):
    discord = config.get("notifications", {}).get("discord", {})
    if not discord.get("enabled"):
        return

    webhook = os.environ.get(discord.get("webhook_url_env", "DISCORD_WEBHOOK_URL")) or discord.get("webhook_url")
    if not webhook:
        raise RuntimeError("Discord webhook URL is not set")

    r = requests.post(webhook, json={"content": message[:1900]}, timeout=30)
    r.raise_for_status()


def send_telegram(config, message):
    telegram = config.get("notifications", {}).get("telegram", {})
    if not telegram.get("enabled"):
        return

    token = os.environ.get(telegram.get("bot_token_env", "TELEGRAM_BOT_TOKEN"))
    chat_id = telegram.get("chat_id") or os.environ.get(telegram.get("chat_id_env", "TELEGRAM_CHAT_ID"))

    if not token or not chat_id:
        raise RuntimeError("Telegram token or chat_id is not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": message[:3900]}, timeout=30)
    r.raise_for_status()


def notify(config, message):
    if (
        config.get("notifications", {}).get("stdout", {}).get("enabled", True)
        and config.get("debug_logging", False)
    ):
        print(f"[DEBUG] Prepared weather alert notification (length={len(message)})")

    for sender in (send_matrix, send_ntfy, send_discord, send_telegram):
        try:
            sender(config, message)
        except Exception as e:
            print(f"NOTIFIER ERROR: {sender.__name__}: {e}", file=sys.stderr)


def load_rss_items(path):
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    items = []

    for part in text.split("<item>")[1:]:
        item = part.split("</item>", 1)[0]

        def tag(name):
            start = f"<{name}>"
            end = f"</{name}>"
            if start in item and end in item:
                return item.split(start, 1)[1].split(end, 1)[0].strip()
            return ""

        items.append({
            "title": tag("title"),
            "link": tag("link"),
            "guid": tag("guid"),
            "pubDate": tag("pubDate"),
            "description": tag("description"),
        })

    return items


def write_rss(config, new_items):
    rss = config.get("rss", {}) or {}
    if not rss.get("enabled"):
        return

    output = Path(rss.get("output_path", "./weather-alerts.xml"))
    max_items = int(rss.get("max_items", 50))

    existing = load_rss_items(output)
    existing_guids = {x.get("guid") for x in existing}

    merged = [x for x in new_items if x["guid"] not in existing_guids]
    merged.extend(existing)
    merged = merged[:max_items]

    build_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    item_xml = []
    for item in merged:
        item_xml.append(f"""
    <item>
      <title>{escape(item['title'])}</title>
      <link>{escape(item['link'])}</link>
      <guid isPermaLink="false">{escape(item['guid'])}</guid>
      <pubDate>{escape(item['pubDate'])}</pubDate>
      <description>{escape(item['description'])}</description>
    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(rss.get('title', 'Weather Alerts'))}</title>
    <link>{escape(rss.get('link', ''))}</link>
    <description>{escape(rss.get('description', 'Weather alerts'))}</description>
    <language>en-us</language>
    <lastBuildDate>{escape(build_date)}</lastBuildDate>
{''.join(item_xml)}
  </channel>
</rss>
"""

    output.write_text(xml, encoding="utf-8")
    print(f"Wrote RSS feed: {output}")


def alert_to_rss_item(feature, message):
    props = feature.get("properties", {})
    headline = props.get("headline") or props.get("event", "Weather Alert")
    alert_id = props.get("id") or feature.get("id") or headline
    link = props.get("@id") or props.get("id") or ""
    sent = props.get("sent") or props.get("effective") or datetime.now(timezone.utc).isoformat()

    try:
        dt = datetime.fromisoformat(sent.replace("Z", "+00:00"))
        pub_date = dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    return {
        "title": headline,
        "link": link,
        "guid": alert_id,
        "pubDate": pub_date,
        "description": message,
    }


def fake_alert():
    return {
        "id": "test-alert",
        "properties": {
            "id": "test-alert",
            "event": "Severe Thunderstorm Warning",
            "severity": "Severe",
            "headline": "Severe Thunderstorm Warning issued for Virginia Beach, VA",
            "areaDesc": "Virginia Beach; Chesapeake Bay Bridge Tunnel",
            "effective": "2026-05-14T12:00:00-04:00",
            "expires": "2026-05-14T13:00:00-04:00",
            "description": "This is a test alert. Strong winds and heavy rain are possible.",
            "instruction": "Move indoors and avoid unnecessary travel.",
            "@id": "https://api.weather.gov/alerts/test-alert",
            "sent": datetime.now(timezone.utc).isoformat(),
        },
    }


def main():
    config = load_config()
    state = load_state()
    rss_items = []

    if "--test" in sys.argv:
        feature = fake_alert()
        location_name = config.get("location", {}).get("name", "configured location")
        message = f"NEW WEATHER ALERT for {location_name}\n\n{format_alert(config, feature, location_name)}"
        notify(config, message)
        rss_items.append(alert_to_rss_item(feature, message))
        write_rss(config, rss_items)
        print("Test notification sent.")
        return

    total_alerts = 0
    new_count = 0

    for location in iter_locations(config):
        lat = location["latitude"]
        lon = location["longitude"]
        name = location.get("name", f"{lat},{lon}")

        alerts = fetch_alerts(lat, lon)
        total_alerts += len(alerts)

        for feature in alerts:
            props = feature.get("properties", {})
            alert_id = props.get("id") or feature.get("id")
            event = props.get("event", "Weather Alert")

            if not alert_id:
                continue
            if not should_include_event(config, event):
                continue
            if quiet_hours_active(config, event):
                continue

            state_key = f"{name}:{alert_id}"
            if state_key in state["seen_alerts"]:
                continue

            message = f"NEW WEATHER ALERT for {name}\n\n{format_alert(config, feature, name)}"
            notify(config, message)
            rss_items.append(alert_to_rss_item(feature, message))

            state["seen_alerts"][state_key] = {
                "event": event,
                "headline": props.get("headline"),
                "location": name,
                "level": event_level(config, event),
                "seen_at": datetime.now(timezone.utc).isoformat(),
            }

            new_count += 1

    save_state(state)
    write_rss(config, rss_items)
    print(f"Checked {total_alerts} active alerts. New alerts: {new_count}")


if __name__ == "__main__":
    main()
