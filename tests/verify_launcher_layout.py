"""Live layout regression check; requires Omarchy, wtype, and an idle desktop.

Opens the launcher and restarts the shell once. Restores the original layout
preference and closes the launcher on completion, including on failure.
"""

import json
import os
import subprocess
import time
from pathlib import Path


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def call(method, argument=""):
    return command("omarchy-shell", "shell", "call", os.environ.get("DICEY_PLUGIN_ID", "dicey.home"), method, argument)


def state():
    return json.loads(call("inspect"))


def wait_shell():
    for _ in range(100):
        try:
            if command("omarchy-shell", "shell", "ping") == "ok":
                # IPC becomes available before asynchronous plugin discovery and
                # bar mounting finish. Let startup settle before the first open.
                time.sleep(2.5)
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(0.05)
    raise AssertionError("The shell did not restart")


def wait_for(predicate):
    latest = {}
    for _ in range(100):
        try:
            latest = state()
            if predicate(latest):
                return latest
        except (ValueError, subprocess.CalledProcessError):
            pass
        time.sleep(0.05)
    raise AssertionError(latest)


def open_menu(route="root", **payload):
    command("omarchy-shell", "shell", "summon", "omarchy.menu", json.dumps({"menu": route, **payload}))
    monitors = json.loads(command("hyprctl", "monitors", "-j"))

    def ready(current):
        monitor = next((monitor for monitor in monitors if monitor["name"] == current.get("screen")), None)
        if not monitor:
            return False
        width = round(monitor["width"] / monitor["scale"])
        height = round(monitor["height"] / monitor["scale"])
        return (current.get("screenWidth") == width and current.get("screenHeight") == height
                and current.get("width", 0) > 0 and current.get("height", 0) > 0)

    # Mapping a layer surface starts with placeholder dimensions, then receives
    # its configured size and monitor. Wait for that before checking geometry.
    return wait_for(lambda current: current.get("opened") and current.get("layoutReady")
                    and current.get("count", 0) > 0 and current.get("route") == route and ready(current))


def wait_saved(current):
    path = Path(current["layoutStatePath"])
    for _ in range(100):
        try:
            if json.loads(path.read_text())["fullscreen"] == current["savedFullscreen"]:
                return
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.02)
    raise AssertionError("The chosen layout was not persisted")


def set_fullscreen(value):
    if state()["savedFullscreen"] != value:
        call("toggleFullscreen")
    current = wait_for(lambda current: current.get("savedFullscreen") == value)
    wait_saved(current)
    return current


original = None
try:
    initial = open_menu()
    assert initial["enhanced"] and not initial["compatibilityError"], initial
    original = initial["savedFullscreen"]
    command("wtype", "-k", "Escape")
    wait_for(lambda current: not current.get("opened"))
    initial = open_menu()
    print("Escape closes the native launcher; shell summon reopens it.")
    if original:
        set_fullscreen(False)
    normal = state()
    assert normal["layout"] == "normal" and normal["width"] < normal["screenWidth"], normal
    normal_width = normal["width"]

    time.sleep(0.15)  # Let the layer-surface keyboard focus settle before input.
    command("wtype", "24 * 7")
    searched = wait_for(lambda current: current.get("filter") == "24 * 7")
    assert searched["rows"][0]["label"] == "168", searched
    time.sleep(0.15)  # Let the layer-surface keyboard focus settle before input.
    command("wtype", "-M", "ctrl", "-M", "shift", "-k", "f", "-m", "shift", "-m", "ctrl")
    expanded = wait_for(lambda current: current.get("layout") == "home"
                        and current.get("width") == current.get("screenWidth")
                        and current.get("height") == current.get("screenHeight"))
    assert expanded["width"] == expanded["screenWidth"], expanded
    assert expanded["height"] == expanded["screenHeight"] and expanded["cardTop"] == 0, expanded
    monitors = json.loads(command("hyprctl", "monitors", "-j"))
    monitor = next(monitor for monitor in monitors if monitor["name"] == expanded["screen"])
    logical_height = round(monitor["height"] / monitor["scale"])
    assert expanded["height"] == logical_height, (expanded, monitor)
    for field in ("filter", "route", "selected", "rows"):
        assert expanded[field] == searched[field], (field, searched[field], expanded[field])
    wait_saved(expanded)
    print("Ctrl+Shift+F fills the entire screen, covering the bar while preserving search and selection.")

    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    # Newer Omarchy versions make Apps an action opening the stock dock, not
    # a menu route. Reopen root there; preserve coverage of the old Apps menu.
    apps_route = "root" if any(row["id"] == "apps" and row["kind"] == "action" for row in initial["rows"]) else "apps"
    apps = open_menu(apps_route)
    assert apps["layout"] == "home" and apps["width"] == apps["screenWidth"], apps
    assert apps["height"] == apps["screenHeight"], apps
    assert apps["hasAppLibrary"] and apps["count"] > 0, apps
    print("Closing and reopening the launcher restores Dicey Home.")

    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    compact = open_menu(mode="select", prompt="Layout check", options=["One", "Two"], width=360)
    assert compact["layout"] == "compact" and compact["width"] < normal["width"], compact
    assert compact["savedFullscreen"] is True, compact
    assert call("toggleFullscreen") == "unavailable"
    print("Compact selection dialogs retain their requested width and the saved preference.")

    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    command("omarchy", "restart", "shell")
    wait_shell()
    restored = open_menu()
    assert restored["layout"] == "home" and restored["savedFullscreen"] is True, restored
    print("A shell restart restores Dicey Home before the first open.")

    # Rapid changes must persist the final value, rather than an earlier write.
    for _ in range(5):
        call("toggleFullscreen")
    normal = wait_for(lambda current: current.get("layout") == "normal")
    wait_saved(normal)
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    normal = open_menu()
    assert normal["layout"] == "normal" and normal["width"] == normal_width, normal
    print("Rapid toggles save the final choice; normal width is restored on reopen.")
finally:
    command("omarchy-shell", "shell", "hide", "omarchy.menu")
    if original is not None:
        open_menu()
        if state()["savedFullscreen"] != original:
            set_fullscreen(original)
        command("omarchy-shell", "shell", "hide", "omarchy.menu")
