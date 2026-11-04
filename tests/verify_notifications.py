"""Deliberate native .dev proof; only synthetic notification files are removed.

Requires an active scripts/dev.py session, wtype, notify-send and a quiet test
desktop. Never invokes shared clear/replay or dismisses real notifications.
Synthetic files are unlinked BEFORE dismiss/action, avoiding host history trim.
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
PREFIX = "Dicey synthetic proof " + str(time.time_ns())
STATE = Path.home() / ".local/state/omarchy/notifications"


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=15).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", PLUGIN, method, argument)


def state():
    return json.loads(call("inspect"))


def wait(predicate, timeout=12):
    deadline = time.monotonic() + timeout
    current = {}
    while time.monotonic() < deadline:
        try:
            current = state()
            if predicate(current):
                return current
        except (ValueError, subprocess.SubprocessError):
            pass
        time.sleep(.08)
    raise AssertionError(current)


def synthetic_files():
    result = []
    for directory in (STATE, STATE / "history"):
        for path in directory.glob("*.json"):
            try:
                row = json.loads(path.read_text())
                if row.get("summary", "").startswith(PREFIX):
                    result.append((path, row))
            except (OSError, ValueError):
                pass
    return result


def remove_synthetic():
    for path, row in synthetic_files():
        assert row["summary"].startswith(PREFIX)
        path.unlink(missing_ok=True)


def real_live_files():
    return [p for p in STATE.glob("*.json") if p not in {p for p, _ in synthetic_files()}]


def history_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (STATE / "history").glob("*.json")}


def send(suffix, action=False):
    args = ["notify-send", "-a", "notify-send", "-u", "critical", "-p"]
    if action:
        args += ["--wait", "--action=default=Verify"]
    return subprocess.Popen(args + [PREFIX + suffix, "Synthetic body <b>plain text</b>"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


before = history_hashes()
senders = []
try:
    assert not real_live_files(), "Real popups present; refusing latest-toast tests."
    command("omarchy-shell", "shell", "summon", PLUGIN, '{"menu":"root","view":"notifications"}')
    initial = wait(lambda s: s.get("home", {}).get("notificationView", {}).get("focused") and s["notifications"]["ready"])
    assert initial["enhanced"] and initial["layout"] == "home", initial
    assert call("paneAction", "notifications:confirmClear") == "unavailable"
    assert call("paneAction", "notifications:clearHistory") == "unavailable"
    assert call("paneAction", "notifications:requestClear") == "confirm"
    wait(lambda s: s["home"]["notificationView"]["confirmingClear"])
    command("wtype", "-k", "Escape")
    wait(lambda s: s["opened"] and not s["home"]["notificationView"]["confirmingClear"])
    print("Notification payload focuses the real feed; Escape cancels clear without deleting.")

    sender = send(" action", action=True)
    senders.append(sender)
    wait(lambda s: s["notifications"]["liveCount"] == 1 and s["notifications"]["urgent"])
    assert synthetic_files(), "Host did not persist synthetic toast"
    assert not real_live_files(), "Real popup arrived; refusing latest action."
    remove_synthetic()
    assert call("paneAction", "notifications:openLatest") == "ok"
    stdout, stderr = sender.communicate(timeout=10)
    assert sender.returncode == 0 and "default" in stdout, (stdout, stderr)
    print("Public latest-toast default action reached the live synthetic sender.")

    sender = send(" dismiss")
    senders.append(sender)
    sender.communicate(timeout=10)
    wait(lambda s: s["notifications"]["liveCount"] == 1)
    assert not real_live_files(), "Real popup arrived; refusing latest dismiss."
    remove_synthetic()
    assert call("paneAction", "notifications:dismissLatest") == "ok"
    wait(lambda s: not s["notifications"]["pending"] and s["notifications"]["liveCount"] == 0)
    print("Public dismiss removes only the synthetic toast; no history is archived/trimmed.")

    sender = send(" lifecycle")
    senders.append(sender)
    sender.communicate(timeout=10)
    live = wait(lambda s: s["notifications"]["liveCount"] == 1 and s["notifications"]["unread"] > 0)
    assert call("paneAction", "notifications:read") == "ok"
    wait(lambda s: s["notifications"]["unread"] == 0)
    keys = live["notifications"]["keys"]
    command("wtype", "-k", "Escape")
    wait(lambda s: not s["opened"])
    command("omarchy", "restart", "shell")
    restored = wait(lambda s: s["notifications"]["ready"] and s["notifications"]["liveCount"] == 1)
    assert restored["notifications"]["unread"] == 0, restored["notifications"]
    assert restored["notifications"]["keys"] == keys, restored["notifications"]
    remove_synthetic()
    command("omarchy-shell", "notifications", "dismiss", PREFIX)
    print("Synthetic critical toast and read watermark survive a fresh shell; Escape closes Home.")
    # No destructive or global-setting commands are used here. DND UI/clear
    # confirmation/deletion are additionally exercised with isolated fixtures.
finally:
    remove_synthetic()
    command("omarchy-shell", "notifications", "dismiss", PREFIX)
    for sender in senders:
        if sender.poll() is None:
            sender.terminate()
            sender.communicate(timeout=5)
    command("omarchy-shell", "shell", "hide", PLUGIN)
    after = history_hashes()
    # A genuine new notification may add/trim history independently. Any such
    # concurrent change invalidates this run rather than silently claiming proof.
    assert before == after, "History changed during proof; inspect before claiming preservation."
    print("PASS: existing real history files are byte-for-byte unchanged.")
