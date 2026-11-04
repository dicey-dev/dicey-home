#!/usr/bin/env python3
"""Read-only, bounded view of Omarchy 4.0.6 notification snapshots.

The host remains the only notification owner/writer. No stored argv, images or
live QObject references cross this boundary. --watch is a shell-owned helper,
not a daemon; it emits only changed snapshots.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import time

MAX_FILES = 256
MAX_BYTES = 65536
NAME = re.compile(r"^(\d{1,16})-(-?\d{1,12})\.json$")


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("Not a bounded regular file")
        raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Oversized snapshot")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Not an object")
        return value


def text(value, limit):
    # Text is rendered with Text.PlainText. Drop control characters (including
    # bidi overrides); do not fetch sender-supplied icons, images or links.
    if not isinstance(value, str):
        return ""
    return "".join(c for c in value[:limit] if c in "\n\t" or
                   (ord(c) >= 32 and not 0x7f <= ord(c) <= 0x9f
                    and not 0x202a <= ord(c) <= 0x202e
                    and not 0x2066 <= ord(c) <= 0x2069))


def snapshot(state):
    rows = {}
    warning = False
    try:
        for live, directory in ((False, state / "notifications/history"),
                                (True, state / "notifications")):
            try:
                names = []
                with os.scandir(directory) as entries:
                    for index, entry in enumerate(entries):
                        if index >= 4096:
                            raise ValueError("Too many snapshot files")
                        match = NAME.fullmatch(entry.name)
                        if match:
                            names.append((int(match[1]), entry.name))
                if len(names) > MAX_FILES:
                    warning = True
                for _, name in sorted(names, reverse=True)[:MAX_FILES]:
                    try:
                        value = read_json(directory / name)
                        timestamp = value.get("timestamp")
                        original_id = value.get("originalId")
                        if (isinstance(timestamp, bool) or not isinstance(timestamp, (int, float))
                                or not math.isfinite(timestamp) or timestamp <= 0
                                or timestamp > time.time() * 1000 + 60000
                                or isinstance(original_id, bool) or not isinstance(original_id, int)
                                or original_id < 0):
                            raise ValueError("Invalid identity")
                        key = f"{int(timestamp)}-{original_id}"
                        if name != key + ".json":
                            raise ValueError("Mismatched identity")
                        rows[key] = {"key": key, "timestamp": timestamp,
                                     "app": text(value.get("app"), 160) or "Unknown app",
                                     "summary": text(value.get("summary"), 512) or "Notification",
                                     "body": text(value.get("body"), 4096),
                                     "urgency": 2 if value.get("urgency") == 2 else 0 if value.get("urgency") == 0 else 1,
                                     "live": live}
                    except FileNotFoundError:
                        pass  # Host archived between listing and read.
                    except (OSError, ValueError, UnicodeError):
                        warning = True
            except FileNotFoundError:
                pass  # First run has no history yet.
        ordered = sorted(rows.values(), key=lambda row: (row["timestamp"], row["key"]), reverse=True)
        warning = warning or len(ordered) > MAX_FILES
        ordered = ordered[:MAX_FILES]
        dnd = None
        try:
            value = read_json(state / "notifications.json").get("dnd")
            if isinstance(value, bool):
                dnd = value
        except FileNotFoundError:
            pass
        except (OSError, ValueError, UnicodeError):
            warning = True
        return {"ready": True, "rows": ordered, "dnd": dnd, "warning": warning, "error": ""}
    except (OSError, ValueError):
        return {"ready": False, "rows": [], "dnd": None, "warning": False,
                "error": "Notification snapshots are unavailable. The host service may be disabled or incompatible."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    # Match the supported host service, which currently uses HOME, not XDG state.
    state = Path.home() / ".local/state/omarchy"
    previous = None
    while True:
        current = json.dumps(snapshot(state), ensure_ascii=True, separators=(",", ":"))
        if current != previous:
            print(current, flush=True)
            previous = current
        if not args.watch:
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
