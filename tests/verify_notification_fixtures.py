"""Native UI proof with isolated notification state in the existing shell.

Run with NO active dev session. Temporarily stages a real runtime source
snapshot via scripts/dev.py, substituting only a test NotificationStore. Real
notification service/data are never called. No second Quickshell is launched.
"""
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dev", ROOT / "scripts/dev.py")
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=15).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", "dicey.home.dev", method, argument)


def wait(predicate):
    deadline = time.monotonic() + 15
    state = {}
    while time.monotonic() < deadline:
        try:
            state = json.loads(call("inspect"))
            if predicate(state):
                return state
        except (ValueError, subprocess.SubprocessError):
            pass
        time.sleep(.05)
    raise AssertionError(state)


if (Path.home() / ".local/state/omarchy/development/dicey.home.json").exists():
    raise SystemExit("Stop the active dev session before running isolated fixtures.")

with tempfile.TemporaryDirectory(prefix="dicey-notification-ui-", dir="/tmp/opencode") as directory:
    source = Path(directory)
    for relative, data in dev.snapshot(ROOT).items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (source / "home/NotificationStore.qml").write_bytes((ROOT / "tests/notification_store_fixture.qml").read_bytes())
    (source / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts/dev.py", source / "scripts/dev.py")
    process = subprocess.Popen(["python3", "-B", str(source / "scripts/dev.py"), "start"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if selector.select(timeout=1):
                line = process.stdout.readline()
                if "Development active:" in line:
                    break
                if not line:
                    raise AssertionError("Development fixture failed to start")
        else:
            raise AssertionError("Development fixture startup timed out")
        command("omarchy", "restart", "shell")
        wait(lambda s: s["notifications"].get("count") == 60)
        command("omarchy-shell", "shell", "summon", "dicey.home.dev", '{"menu":"root","view":"notifications"}')
        state = wait(lambda s: s.get("home", {}).get("notificationView", {}).get("focused"))
        groups = state["notifications"]["groups"]
        assert groups[0] == "app:synthetic-mail" and "site:news.example.com" in groups and "webapp:web.whatsapp.com" in groups, groups
        keys = state["notifications"]["keys"]
        assert keys[0] == "synthetic-0" and keys[1] == "synthetic-4", keys  # Grouped, newest first.
        print("PASS grouping: apps, browser sites and installed web apps form contiguous newest-first groups.")
        # The payload focuses the feed itself. Read older entries, then arrive.
        command("wtype", "-k", "Next", "-k", "Down", "-k", "Down")
        before = wait(lambda s: s["home"]["notificationView"]["feed"]["topKey"] not in ("", "synthetic-0"))["home"]["notificationView"]["feed"]
        call("paneAction", "notifications:dndOn")  # Fixture-only arrival + live-to-history update.
        after = wait(lambda s: s["notifications"]["count"] == 61)["home"]["notificationView"]["feed"]
        assert after["topKey"] == before["topKey"] and abs(after["offset"] - before["offset"]) < 1, (before, after)
        assert after["currentKey"] == before["currentKey"], (before, after)
        print("PASS native scroll/current-key preservation across arrival + live-to-history update.")
        # Delete removes the selected entry; Shift+Delete clears its group.
        selected = after["currentKey"]
        order = json.loads(call("inspect"))["notifications"]["keys"]
        successor = order[order.index(selected) + 1]
        command("wtype", "-k", "Delete")
        state = wait(lambda s: s["notifications"]["count"] == 60)
        assert selected not in state["notifications"]["keys"], state["notifications"]
        assert state["home"]["notificationView"]["feed"]["currentKey"] == successor, (successor, state["home"]["notificationView"]["feed"])
        before_groups = state["notifications"]["groups"]  # Includes the fixture arrival's group.
        command("wtype", "-M", "shift", "-k", "Delete", "-m", "shift")
        state = wait(lambda s: len(s["notifications"]["groups"]) == len(before_groups) - 1)
        assert state["notifications"]["count"] < 59, state["notifications"]
        print("PASS keyboard removal: Delete removes one entry, Shift+Delete clears that entry's group.")
        assert call("paneAction", "notifications:remove:missing") == "unavailable"
        assert call("paneAction", "notifications:clearGroup:app:missing") == "unavailable"
        assert call("paneAction", "notifications:clearGroup:__proto__") == "unavailable"
        first = state["notifications"]["keys"][0]
        assert call("paneAction", "notifications:remove:" + first) == "ok"
        site = next(g for g in state["notifications"]["groups"] if g.startswith("site:"))
        assert call("paneAction", "notifications:clearGroup:" + site) == "ok"
        state = wait(lambda s: site not in s["notifications"]["groups"])
        assert first not in state["notifications"]["keys"]
        call("paneAction", "notifications:dndOff")
        wait(lambda s: s["notifications"]["dnd"] is False)
        screenshot = os.environ.get("DICEY_FIXTURE_SCREENSHOT")
        if screenshot:
            command("grim", screenshot)
        assert call("paneAction", "notifications:clearAll") == "ok"
        state = wait(lambda s: s["notifications"]["count"] == 0)
        assert state["notifications"]["total"] == 61 and call("paneAction", "notifications:clearAll") == "unavailable"
        print("PASS isolated per-entry/group/all removal, DND toggle and empty state; fixture rows are only hidden.")
        empty = os.environ.get("DICEY_FIXTURE_EMPTY_SCREENSHOT")
        if empty:
            command("grim", empty)
    finally:
        command("omarchy-shell", "shell", "hide", "dicey.home.dev")
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=40)
        selector.close()
        assert process.returncode == 0, output
        command("omarchy", "restart", "shell")
        print("Fixture dev activation restored; real notification service was not called.")
