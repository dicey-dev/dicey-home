#!/usr/bin/env python3
"""Read-only, bounded view of Omarchy 4.5 notification state.

The host remains the only notification owner/writer. Home reads its live.json
and history.json, never its stored argv, images or live QObject references.
Rows are grouped by application; browser notifications are grouped by website,
and a website installed as an Omarchy web app takes that web app's name.
--watch is a shell-owned helper, not a daemon; it emits only changed snapshots.
"""
import argparse
import html
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from urllib.parse import urlsplit

MAX_ROWS = 256
MAX_BYTES = 8 * 1024 * 1024  # Host caps rows in UTF-16 units: 100 live x 16 Ki, 100 history x 4 Ki.
RETENTION = 24 * 3600  # Host history keeps 24 hours (Store.retain), pruned only on writes.
HISTORY_LIMIT = 100
MAX_DESKTOP_FILES = 512
MAX_DESKTOP_BYTES = 65536
KEY = re.compile(r"^[A-Za-z0-9_-]{1,120}$")
# Mirrors the host's own browser list (plugins/notifications/Markup.js).
BROWSERS = re.compile(r"^(google chrome|chromium|brave|brave browser|brave origin|microsoft edge|"
                      r"vivaldi|opera|helium|firefox|zen|librewolf)$", re.I)
LABEL = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)$")
MARKUP = re.compile(r"</?(?:a|b|i|u|s|em|strong|br|img|span|p|font|tt|code)\b[^>]*>", re.I)
WEBAPP = re.compile(r"""(?:omarchy-launch-webapp\s+|--app=)["']?(https?://[^\s"']+)""")


def read_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("Not a bounded regular file")
        raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Oversized file")
        return raw


def read_rows(path):
    """A host store file: a JSON array of objects. Missing or empty is no rows."""
    try:
        raw = read_bytes(path, MAX_BYTES)
    except FileNotFoundError:
        return []
    if not raw.strip():
        return []
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Not an array")
    return value


def text(value, limit):
    # Rendered with Text.PlainText. Drop control characters (including bidi
    # overrides); never fetch sender-supplied icons, images or links.
    if not isinstance(value, str):
        return ""
    return "".join(c for c in value[:limit] if c in "\n\t" or
                   (ord(c) >= 32 and not 0x7f <= ord(c) <= 0x9f
                    and not 0x202a <= ord(c) <= 0x202e
                    and not 0x2066 <= ord(c) <= 0x2069))


def plain(value, limit):
    """The host keeps a small markup subset in bodies; show its text, not its tags."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"<br\s*/?>", "\n", value[:limit * 2], flags=re.I)
    value = html.unescape(MARKUP.sub("", value))
    return text(re.sub(r"[ \t]+", " ", value).strip(), limit)


def hostname(value):
    """The host's canonicalHostname(): a DNS name, never an IP-looking label."""
    if not isinstance(value, str) or len(value) > 253:
        return ""
    name = value.lower().rstrip(".")
    labels = name.split(".")
    if len(labels) < 2 or not all(LABEL.fullmatch(label) for label in labels):
        return ""
    if re.fullmatch(r"0x[0-9a-f]*|[0-9]+", labels[-1]):
        return ""
    return name


def app_id(value):
    """A stable group id; names without ASCII letters keep their own text."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug if slug and value.isascii() else value.casefold()


def site_of(name):
    """A hostname with a leading www. merged into its site (but www.com stays)."""
    short = name.removeprefix("www.")
    return short if "." in short else name


def group(app, source, webapps):
    """(id, label, kind, browser) for one notification."""
    if BROWSERS.fullmatch(app.strip()):
        site = site_of(hostname(source) if source != app else "")
        if site:
            name = webapps.get(site)
            if name:
                return "webapp:" + site, name, "webapp", app
            return "site:" + site, site, "site", app
    return "app:" + app_id(app), app, "app", ""


def desktop_webapps(directory):
    """Omarchy web apps: hostname -> desktop entry Name, from omarchy-launch-webapp entries."""
    found = {}
    try:
        with os.scandir(directory) as entries:
            names = sorted(entry.name for entry in entries if entry.name.endswith(".desktop"))
    except OSError:
        return found  # Web app names are optional; never disable the reader.
    for name in names[:MAX_DESKTOP_FILES]:
        try:
            content = read_bytes(directory / name, MAX_DESKTOP_BYTES).decode("utf-8")
        except (OSError, ValueError, UnicodeError):
            continue
        label = url = ""
        section = ""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("["):
                section = line
            elif section == "[Desktop Entry]":
                if line.startswith("Name=") and not label:
                    label = text(line[5:], 80).strip()
                elif line.startswith("Exec=") and not url:
                    match = WEBAPP.search(line)
                    url = match[1] if match else ""
        try:
            site = site_of(hostname(urlsplit(url).hostname or "") if url else "")
        except ValueError:
            site = ""
        if label and site and site not in found:
            found[site] = label
    return found


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def row_from(value, live, now_ms, webapps):
    if not isinstance(value, dict):
        raise ValueError("Not an object")
    key, ts = value.get("key"), value.get("ts")
    if (not isinstance(key, str) or not KEY.fullmatch(key) or not finite(ts) or ts <= 0
            or ts * 1000 > now_ms + 60000 or (not live and not finite(value.get("closed_ts")))):
        raise ValueError("Invalid identity")
    app = text(value.get("app"), 160).strip() or "Unknown app"
    source = text(value.get("source"), 253).strip()
    group_id, label, kind, browser = group(app, source, webapps)
    urgency = value.get("urgency")
    return {"key": key, "timestamp": int(ts * 1000), "app": app,
            "summary": text(value.get("summary"), 512).strip() or "Notification",
            "body": plain(value.get("body"), 4096),
            "urgency": 2 if urgency == 2 else 0 if urgency == 0 else 1, "live": live,
            "group": group_id, "groupLabel": label, "groupKind": kind, "browser": browser}


def snapshot(state, applications, webapps=None):
    webapps = desktop_webapps(applications) if webapps is None else webapps
    now_ms = time.time() * 1000
    rows = {}
    warning = False
    try:
        cutoff = now_ms / 1000 - RETENTION
        # History (newest first) before live, so a row both closing and live
        # (mid-write) shows as live; a replayed key keeps its newest copy.
        for live, name in ((False, "history.json"), (True, "live.json")):
            kept = 0
            for value in read_rows(state / "notifications" / name):
                try:
                    row = row_from(value, live, now_ms, webapps)
                except ValueError:
                    warning = True
                    continue
                if not live:
                    # The host prunes history only when it writes; mirror its retention.
                    if row["key"] in rows or value["closed_ts"] <= cutoff or kept >= HISTORY_LIMIT:
                        continue
                    kept += 1
                rows[row["key"]] = row
    except (OSError, ValueError, UnicodeError, RecursionError):
        return {"ready": False, "rows": [], "warning": False,
                "error": "Notification history is unavailable. The host service may be disabled or incompatible."}
    ordered = sorted(rows.values(), key=lambda row: (row["timestamp"], row["key"]), reverse=True)
    warning = warning or len(ordered) > MAX_ROWS
    return {"ready": True, "rows": ordered[:MAX_ROWS], "warning": warning, "error": ""}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    # Match the supported host service, which uses HOME, not XDG state.
    state = Path.home() / ".local/state/omarchy"
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    applications = data / "applications"
    previous, webapps, scanned = None, {}, 0.0
    while True:
        if time.monotonic() - scanned > 30:
            webapps, scanned = desktop_webapps(applications), time.monotonic()
        current = json.dumps(snapshot(state, applications, webapps), ensure_ascii=True, separators=(",", ":"))
        if current != previous:
            print(current, flush=True)
            previous = current
        if not args.watch:
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
