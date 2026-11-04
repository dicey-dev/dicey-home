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
        wait(lambda s: s["notifications"].get("count") == 105)
        command("omarchy-shell", "shell", "summon", "dicey.home.dev", '{"menu":"root","view":"notifications"}')
        state = wait(lambda s: s.get("home", {}).get("notificationView", {}).get("focused"))
        assert state["notifications"]["badge"] == "99+" and state["notifications"]["urgent"]
        # Tab from filter -> read -> DND -> feed, then read older entries.
        command("wtype", "-k", "Tab", "-k", "Tab", "-k", "Tab", "-k", "Next")
        before = wait(lambda s: s["home"]["notificationView"]["feed"]["topKey"] not in ("", "synthetic-0"))["home"]["notificationView"]["feed"]
        call("paneAction", "notifications:replay")  # Fixture-only snapshot arrival/archive.
        after = wait(lambda s: s["notifications"]["count"] == 106)["home"]["notificationView"]["feed"]
        assert after["topKey"] == before["topKey"] and abs(after["offset"] - before["offset"]) < 1, (before, after)
        assert after["currentKey"] == before["currentKey"], (before, after)
        print("PASS native scroll/current-key preservation across arrival + live-to-history update.")
        assert call("paneAction", "notifications:confirmClear") == "unavailable"
        assert call("paneAction", "notifications:clearHistory") == "unavailable"
        assert call("paneAction", "notifications:requestClear") == "confirm"
        wait(lambda s: s["home"]["notificationView"]["confirmingClear"])
        # Cancel has default focus. Enter must cancel, not delete.
        command("wtype", "-k", "Return")
        wait(lambda s: not s["home"]["notificationView"]["confirmingClear"])
        assert json.loads(call("inspect"))["notifications"]["count"] == 106
        call("paneAction", "notifications:requestClear")
        command("wtype", "-k", "Tab", "-k", "Return")
        state = wait(lambda s: s["notifications"]["count"] == 1)
        assert state["notifications"]["lastCommand"] == "clearHistory" and state["notifications"]["liveCount"] == 1
        print("PASS isolated native clear: default Enter cancels; Tab+Enter confirms; live entry retained.")
        call("paneAction", "notifications:dndOn")
        wait(lambda s: s["notifications"]["dnd"] is True)
        call("paneAction", "notifications:dndOff")
        wait(lambda s: s["notifications"]["dnd"] is False)
        call("paneAction", "notifications:read")
        wait(lambda s: s["notifications"]["unread"] == 0)
        # Exercise the actual first filter button via its payload-provided focus.
        call("paneAction", "notifications:view")
        command("wtype", "-k", "Return")
        wait(lambda s: s["home"]["notificationView"]["unreadOnly"])
        print("PASS isolated count cap, urgency, DND toggle, read/filter and empty-unread state.")
        screenshot = os.environ.get("DICEY_FIXTURE_SCREENSHOT")
        if screenshot:
            command("grim", screenshot)
    finally:
        command("omarchy-shell", "shell", "hide", "dicey.home.dev")
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=40)
        selector.close()
        assert process.returncode == 0, output
        command("omarchy", "restart", "shell")
        print("Fixture dev activation restored; real notification service was not called.")
