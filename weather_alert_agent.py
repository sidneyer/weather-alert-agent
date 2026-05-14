#!/usr/bin/env python3
import json
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from xml.sax.saxutils import escape

import requests
import yaml

CONFIG_FILE = Path("config.yaml")
STATE_FILE = Path("state.json")
USER_AGENT = "weather-alert-agent/0.1 (local testing)"



def load_rss_items(path):
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    items = []

    parts = text.split("<item>")
    for part in parts[1:]:
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


def write_rss(config, new_alert_items):
    rss = config.get("rss", {})
    if not rss.get("enabled"):
        return

    output_path = Path(rss.get("output_path", "./weather-alerts.xml"))
    max_items = int(rss.get("max_items", 50))

    existing = load_rss_items(output_path)
    existing_guids = {x.get("guid") for x in existing}

    merged = []
    for item in new_alert_items:
        if item["guid"] not in existing_guids:
            merged.append(item)

    merged.extend(existing)
    merged = merged[:max_items]

    channel_title = rss.get("title", "Weather Alerts")
    channel_link = rss.get("link", "")
    channel_description = rss.get("description", "Weather alerts")
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
    <title>{escape(channel_title)}</title>
    <link>{escape(channel_link)}</link>
    <description>{escape(channel_description)}</description>
    <language>en-us</language>
    <lastBuildDate>{escape(build_date)}</lastBuildDate>
{''.join(item_xml)}
  </channel>
</rss>
"""

    output_path.write_text(xml, encoding="utf-8")
    print(f"Wrote RSS feed: {output_path}")


def alert_to_rss_item(config, feature, message):
    props = feature.get("properties", {})
    event = props.get("event", "Weather Alert")
    headline = props.get("headline") or event
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
    return nws_get(f"https://api.weather.gov/alerts/active?point={lat},{lon}").get("features", [])


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

    r = requests.post(
        f"{server}/{topic}",
        data=message.encode("utf-8"),
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()


def format_alert(feature):
    props = feature.get("properties", {})

    event = props.get("event", "Weather Alert")
    severity = props.get("severity", "Unknown")
    headline = props.get("headline") or event
    area = props.get("areaDesc", "Unknown area")
    expires = props.get("expires", "")
    description = (props.get("description") or "").strip().replace("\n", " ")
    instruction = (props.get("instruction") or "").strip()
    url = props.get("@id") or props.get("id") or ""

    if len(description) > 500:
        description = description[:500].rsplit(" ", 1)[0] + "..."

    lines = [
        f"⚠️ {event}",
        "",
        headline,
        "",
        f"Area: {area}",
        f"Severity: {severity}",
        f"Expires: {expires}",
    ]

    if description:
        lines += ["", description]

    if instruction:
        lines += ["", "Recommended action:", instruction]

    if url:
        lines += ["", f"Official source: {url}"]

    return "\n".join(lines)


def fake_alert():
    return {
        "id": "test-alert",
        "properties": {
            "id": "test-alert",
            "event": "Severe Thunderstorm Warning",
            "severity": "Severe",
            "urgency": "Immediate",
            "certainty": "Likely",
            "headline": "Severe Thunderstorm Warning issued for Norfolk, VA",
            "areaDesc": "Norfolk; Portsmouth; Chesapeake",
            "effective": "2026-05-14T12:00:00-04:00",
            "expires": "2026-05-14T13:00:00-04:00",
            "description": "This is a test alert. Strong winds and heavy rain are possible.",
            "instruction": "Move indoors and avoid unnecessary travel.",
            "@id": "https://api.weather.gov/alerts/test-alert",
        },
    }


def notify(config, message):
    if config.get("notifications", {}).get("stdout", {}).get("enabled", True):
        print(message)
    send_matrix(config, message)
    send_ntfy(config, message)


def main():
    config = load_config()
    rss_items = []

    if "--test" in sys.argv:
        feature = fake_alert()
        message = f"NEW WEATHER ALERT for {config['location'].get('name', 'configured location')}\n\n{format_alert(feature)}"
        notify(config, message)
        rss_items.append(alert_to_rss_item(config, feature, message))
        print("Test notification sent.")
        return

    state = load_state()
    lat = config["location"]["latitude"]
    lon = config["location"]["longitude"]
    name = config["location"].get("name", f"{lat},{lon}")
    include = set(config.get("alerts", {}).get("include", []) or [])

    alerts = fetch_alerts(lat, lon)
    new_count = 0
    rss_items = []

    for feature in alerts:
        props = feature.get("properties", {})
        alert_id = props.get("id") or feature.get("id")
        event = props.get("event", "Weather Alert")

        if not alert_id:
            continue
        if include and event not in include:
            continue
        if alert_id in state["seen_alerts"]:
            continue

        message = f"NEW WEATHER ALERT for {name}\n\n{format_alert(feature)}"
        notify(config, message)
        rss_items.append(alert_to_rss_item(config, feature, message))

        state["seen_alerts"][alert_id] = {
            "event": event,
            "headline": props.get("headline"),
            "seen_at": datetime.now(timezone.utc).isoformat(),
        }
        new_count += 1

    save_state(state)
    write_rss(config, rss_items)
    print(f"Checked {len(alerts)} active alerts. New alerts: {new_count}")


if __name__ == "__main__":
    main()
