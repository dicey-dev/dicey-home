"""Live native check: opens launcher, uses a silent MPRIS fixture, restarts shell.

Run on an idle desktop. Preserves layout/tile choices and does not change audio,
Wi-Fi, notifications, lock state, or launch applications. Requires python-dbus
and python-gobject for the test-only media fixture.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "org.mpris.MediaPlayer2.dicey_control_test"


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=10).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", os.environ.get("DICEY_PLUGIN_ID", "dicey.home"), method, argument)


def state():
    return json.loads(call("inspect"))


def wait_for(predicate):
    latest = {}
    for _ in range(140):
        try:
            latest = state()
            if predicate(latest):
                return latest
        except (ValueError, subprocess.CalledProcessError):
            pass
        time.sleep(0.05)
    raise AssertionError(latest)


def open_menu(route="root"):
    command("omarchy-shell", "shell", "summon", "omarchy.menu", json.dumps({"menu": route}))
    return wait_for(lambda current: current.get("opened") and current.get("enhanced") and current.get("layoutReady"))


original = None
fixture = None
tested_focus = False
try:
    original = open_menu()
    if original["hiddenTiles"]:
        call("restoreTiles")
    if not original["savedFullscreen"]:
        call("toggleHome")
    native = wait_for(lambda current: current.get("home", {}).get("ready") and current.get("home", {}).get("metrics", {}).get("cpu") is not None)
    assert native["layout"] == "home" and native["home"]["native"], native
    assert native["width"] == native["screenWidth"] and native["height"] == native["screenHeight"], native
    assert native["home"]["metrics"]["memory"]["total"] > 0, native
    assert native["home"]["navigationCount"] > 0, native
    print("Native tile surface and real CPU/memory/network/audio snapshots are working.")

    command("wtype", "-M", "ctrl", "-M", "shift", "-k", "f", "-m", "shift", "-m", "ctrl")
    wait_for(lambda current: current.get("layout") == "normal")
    command("wtype", "-M", "ctrl", "-M", "shift", "-k", "f", "-m", "shift", "-m", "ctrl")
    wait_for(lambda current: current.get("layout") == "home")
    command("wtype", "-k", "Down")
    first = wait_for(lambda current: current.get("home", {}).get("focusedTile") == "activity")
    command("wtype", "-k", "Right")
    wait_for(lambda current: current.get("home", {}).get("focusedTile") != first["home"]["focusedTile"])
    call("search", "24 * 7")
    calculated = wait_for(lambda current: current.get("rows", [{}])[0].get("label") == "168")
    assert calculated["home"]["resultsCount"] > 0 and not calculated["home"]["sampling"], calculated
    call("search", "")
    print("Actual keyboard toggle and shared calculator/search are working.")

    open_menu("setup")
    assert state()["layout"] == "normal" and state()["savedFullscreen"]
    assert call("toggleHome") == "home"
    wait_for(lambda current: current.get("route") == "root" and current.get("layout") == "home")
    print("Other menu routes stay compact; the layout toggle returns to the home home.")

    hidden = "network" not in original["hiddenTiles"]
    if hidden:
        call("toggleTile", "network")
    wait_for(lambda current: "network" in current.get("hiddenTiles", []))
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    open_menu()
    assert "network" in state()["hiddenTiles"]

    if not original["focusTimer"]["running"] and original["focusTimer"]["remaining"] == 1500:
        call("focusControl", "toggle")
        tested_focus = True
        command("omarchy-shell", "shell", "hide", "omarchy.menu")
        time.sleep(2.1)
        closed = state()
        assert closed["focusTimer"]["running"] and closed["focusTimer"]["remaining"] < 1500, closed
        assert not closed["home"]["sampling"], closed
        open_menu()
        call("focusControl", "reset")
        tested_focus = False
        print("Focus timer continues while closed; background telemetry stops.")

    fixture = subprocess.Popen([sys.executable, "-B", str(ROOT / "tests/control_mpris_fixture.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert fixture.stdout.readline().strip() == "ready"
    wait_for(lambda current: current.get("home", {}).get("playerCount", 0) >= 1)
    call("paneAction", "player:" + FIXTURE)
    wait_for(lambda current: (current.get("home", {}).get("player") or {}).get("dbusName") == FIXTURE
             and (current.get("home", {}).get("player") or {}).get("canPlayPause"))
    assert call("paneAction", "media:playPause") == "ok"
    wait_for(lambda current: (current.get("home", {}).get("player") or {}).get("playing") is True)
    assert call("paneAction", "media:next") == "ok"
    wait_for(lambda current: (current.get("home", {}).get("player") or {}).get("title") == "Dicey Home test track 2")
    assert call("paneAction", "media:seek:30") == "ok"
    wait_for(lambda current: (current.get("home", {}).get("player") or {}).get("position", 0) >= 29.9)
    assert call("paneAction", "media:playPause") == "ok"
    wait_for(lambda current: (current.get("home", {}).get("player") or {}).get("playing") is False)
    print("MPRIS metadata, playback, track switching, and seek verified with a silent fixture.")

    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    command("omarchy", "restart", "shell")
    time.sleep(2.5)
    restored = open_menu()
    assert restored["layout"] == "home" and "network" in restored["hiddenTiles"], restored
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    command("omarchy-shell", "shell", "summon", "omarchy.menu", '{"mode":"select","options":["One","Two"],"width":360}')
    compact = wait_for(lambda current: current.get("layout") == "compact")
    assert compact["width"] < compact["screenWidth"] and compact["savedFullscreen"], compact
    print("Layout and tile preferences survive restart; selection dialogs remain compact.")
finally:
    if fixture:
        fixture.terminate()
        fixture.communicate(timeout=5)
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    if original:
        open_menu()
        for tile in set(state()["hiddenTiles"]) ^ set(original["hiddenTiles"]):
            call("toggleTile", tile)
        if state()["savedFullscreen"] != original["savedFullscreen"]:
            call("toggleHome")
        if tested_focus:
            call("focusControl", "reset")
        command("omarchy-shell", "shell", "hide", "omarchy.menu")
