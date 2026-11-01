"""Idle-desktop check for input latency, batched results, and fullscreen bounds."""
import json
import subprocess
import time


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", "dicey.home", method, argument)


def state():
    return json.loads(call("inspect"))


original = None
try:
    command("omarchy-shell", "shell", "summon", "omarchy.menu", '{"menu":"root"}')
    for _ in range(80):
        current = state()
        if current.get("opened") and current.get("enhanced"):
            break
        time.sleep(0.05)
    original = current["savedFullscreen"]
    if not original:
        call("toggleHome")
    time.sleep(0.3)
    current = state()
    geometry = current["home"]["geometry"]
    assert geometry["width"] == current["screenWidth"] and geometry["height"] == current["screenHeight"], current
    monitors = json.loads(command("hyprctl", "monitors", "-j"))
    monitor = next(item for item in monitors if item["name"] == current["screen"])
    assert geometry["height"] == round(monitor["height"] / monitor["scale"])
    assert geometry["width"] == round(monitor["width"] / monitor["scale"])
    layers = json.loads(command("hyprctl", "layers", "-j"))
    overlay = next(layer for layer in layers[current["screen"]]["levels"]["3"] if layer["namespace"] == "omarchy-menu")
    assert overlay["x"] == monitor["x"] and overlay["y"] == monitor["y"], (overlay, monitor)
    assert overlay["w"] == geometry["width"] and overlay["h"] == geometry["height"], (overlay, geometry)
    print("Fullscreen overlay:", geometry["width"], "x", geometry["height"], "at the display origin, covering the bar.")

    call("search", "")
    time.sleep(0.1)
    before = state()["home"]["resultPublications"]
    started = time.monotonic()
    command("wtype", "-d", "5", "applications")
    typed = state()
    latency = time.monotonic() - started
    assert typed["home"]["input"] == "applications", typed
    assert latency < 0.5, f"Typing burst blocked for {latency:.3f}s"
    time.sleep(0.15)
    settled = state()
    assert settled["filter"] == "applications", settled
    publications = settled["home"]["resultPublications"] - before
    assert publications <= 4, f"Results republished {publications} times for a typing burst"
    print(f"12-character typing burst including IPC inspection: {latency * 1000:.0f}ms; {publications} result publications.")

    call("search", "")
    command("wtype", "-d", "1", "code", "-k", "Down")
    for _ in range(40):
        selected = state()
        if selected["home"]["focusedTile"] == "result:0":
            break
        time.sleep(0.02)
    assert selected["filter"] == "code" and selected["home"]["focusedTile"] == "result:0", selected
    print("Immediate Down after a typing burst flushes the latest query before selecting its first result.")
    command("wtype", "-k", "Escape")

    for query in ("a", "s", "code", "24 * 7", "", "firefox"):
        started = time.monotonic()
        call("search", query)
        elapsed = time.monotonic() - started
        time.sleep(0.08)
        latest = state()
        assert latest["home"]["input"] == query, latest
        assert latest["filter"] == query, latest
        assert latest["home"]["liveResultDelegates"] <= 100, latest
        assert elapsed < 0.5, (query, elapsed)
        print(f"{query or '(clear)'!r}: {elapsed * 1000:.0f}ms IPC search; {latest['count']} results / {latest['home']['liveResultDelegates']} instantiated tiles.")
finally:
    if original is not None:
        if state()["savedFullscreen"] != original:
            call("toggleHome")
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
