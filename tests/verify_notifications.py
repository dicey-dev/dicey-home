"""Deliberate native .dev proof against the real Omarchy notification service.

Requires an active `scripts/dev.py start` session, notify-send and grim. It
sends a few uniquely prefixed synthetic notifications (they expire into the
host's own history, which keeps them at most 24 hours) and never clears,
dismisses or writes the host's notification files. Real entries must be
byte-for-byte unchanged afterwards.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

PLUGIN = os.environ.get("DICEY_PLUGIN_ID", "")
if PLUGIN != "dicey.home.dev":
    raise SystemExit("Run only with DICEY_PLUGIN_ID=dicey.home.dev and an active dev session.")
RUN = str(time.time_ns())
PREFIX = "Dicey synthetic proof " + RUN
STORE = Path.home() / ".local/state/omarchy/notifications"
SCREENSHOT = os.environ.get("DICEY_PROOF_SCREENSHOT", "")


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=20).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", PLUGIN, method, argument)


def state():
    return json.loads(call("inspect"))


def wait(predicate, timeout=20):
    deadline = time.monotonic() + timeout
    current = {}
    while time.monotonic() < deadline:
        try:
            current = state()
            if predicate(current):
                return current
        except (ValueError, subprocess.SubprocessError):
            pass
        time.sleep(.1)
    raise AssertionError(current)


def host_rows():
    rows = []
    for name in ("history.json", "live.json"):
        raw = (STORE / name).read_text()
        rows += json.loads(raw) if raw.strip() else []
    return rows


def synthetic():
    return {row["summary"]: row["key"] for row in host_rows() if str(row.get("summary", "")).startswith(PREFIX)}


def real_history():
    raw = (STORE / "history.json").read_text()
    rows = json.loads(raw) if raw.strip() else []
    return {row["key"]: hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            for row in rows if not str(row.get("summary", "")).startswith("Dicey synthetic proof")}


def send(app, suffix, body):
    command("notify-send", "-a", app, "-t", "1500", PREFIX + suffix, body)


history = json.loads((STORE / "history.json").read_text() or "[]")
assert len(history) < 90, "Host history is nearly full; synthetic entries could trim real ones."
before = real_history()
mail, chat = "Dicey Proof Mail " + RUN, "Dicey Proof Chat " + RUN
send(mail, " mail 1", "First synthetic mail")
send(chat, " chat", "Synthetic chat body <b>bold</b> &amp; plain")
send(mail, " mail 2", "Second synthetic mail")
# Chromium labels a site notification with a leading origin anchor; the host lifts it.
send("Chromium", " site", '<a href="https://news.example.com/">news.example.com</a>Synthetic site body')
deadline = time.monotonic() + 20
while len(synthetic()) < 4 and time.monotonic() < deadline:
    time.sleep(.2)
keys = synthetic()
assert len(keys) == 4, keys
mail_group, chat_group = "app:dicey-proof-mail-" + RUN, "app:dicey-proof-chat-" + RUN
site_group = "site:news.example.com"
current = wait(lambda s: s["notifications"]["ready"] and all(k in s["notifications"]["keys"] for k in keys.values()))
groups = current["notifications"]["groups"]
assert {mail_group, chat_group, site_group} <= set(groups), groups
order = current["notifications"]["keys"]
mail_keys = [keys[PREFIX + " mail 2"], keys[PREFIX + " mail 1"]]
start = order.index(mail_keys[0])
assert order[start:start + 2] == mail_keys, order
print("PASS real host: synthetic app and Chromium site notifications are grouped by app and website.")

command("omarchy-shell", "shell", "summon", PLUGIN, '{"menu":"root","view":"notifications"}')
wait(lambda s: s.get("home", {}).get("notificationView", {}).get("focused"))
time.sleep(.6)
if SCREENSHOT:
    command("grim", SCREENSHOT)

assert call("paneAction", "notifications:remove:" + keys[PREFIX + " chat"]) == "ok"
assert call("paneAction", "notifications:clearGroup:" + site_group) == "ok"
current = wait(lambda s: keys[PREFIX + " chat"] not in s["notifications"]["keys"]
               and site_group not in s["notifications"]["groups"])
assert all(k in current["notifications"]["keys"] for k in mail_keys)
assert len(synthetic()) == 4, "Home must not change host history"
print("PASS remove/clear group hide entries in Home only; host history still holds them.")

command("omarchy-shell", "shell", "hide", PLUGIN)
command("omarchy", "restart", "shell")
current = wait(lambda s: s["notifications"]["ready"] and all(k in s["notifications"]["keys"] for k in mail_keys), 40)
assert keys[PREFIX + " chat"] not in current["notifications"]["keys"] and site_group not in current["notifications"]["groups"]
print("PASS removals persist across a fresh shell.")

assert call("paneAction", "notifications:clearGroup:" + mail_group) == "ok"
wait(lambda s: not any(k in s["notifications"]["keys"] for k in keys.values()))
after = real_history()
assert all(after.get(key) == digest for key, digest in before.items()), "A real history entry changed"
print("PASS real history entries are unchanged; synthetic entries expire from host history within 24 hours.")
