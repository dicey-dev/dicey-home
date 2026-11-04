"""Read-only Linux activity snapshots and explicit audio actions for Dicey Home."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time


def read(path):
    try:
        return Path(path).read_text()
    except OSError:
        return ""


def cpu_ticks(text):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if parts and re.fullmatch(r"cpu\d*", parts[0]) and len(parts) >= 5:
            numbers = [int(value) for value in parts[1:9]]
            result[parts[0]] = (sum(numbers), numbers[3] + (numbers[4] if len(numbers) > 4 else 0))
    return result


def cpu_usage(previous, current):
    values = {}
    for name, (total, idle) in current.items():
        before = previous.get(name)
        elapsed = total - before[0] if before else 0
        values[name] = round(max(0, min(100, (1 - (idle - before[1]) / elapsed) * 100)), 1) if elapsed > 0 else None
    return values


def memory(text):
    values = {key: int(value) * 1024 for key, value in re.findall(r"^(\w+):\s+(\d+)\s+kB", text, re.MULTILINE)}
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", sum(values.get(key, 0) for key in ("MemFree", "Buffers", "Cached")))
    return {"total": total, "used": max(0, total - available)}


def net_counters(text):
    counters = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, data = line.split(":", 1)
        fields = data.split()
        if len(fields) >= 16 and name.strip() != "lo":
            counters[name.strip()] = (int(fields[0]), int(fields[8]))
    return counters


def command(arguments):
    try:
        return subprocess.run(arguments, capture_output=True, text=True, timeout=0.8, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def audio_sink():
    return command(["omarchy-audio-output-sink"]) or "@DEFAULT_SINK@"


def audio_state():
    sink = audio_sink()
    volume = command(["pactl", "get-sink-volume", sink])
    percentages = [int(value) for value in re.findall(r"/\s*(\d+)%", volume)]
    mute = command(["pactl", "get-sink-mute", sink])
    return {"available": bool(percentages), "volume": round(sum(percentages) / len(percentages)) if percentages else 0,
            "muted": mute.endswith("yes"), "sink": sink}


def temperature():
    preferred, fallback = [], []
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        try:
            value = float(read(zone / "temp").strip()) / 1000
        except ValueError:
            continue
        if not 0 < value < 150:
            continue
        kind = read(zone / "type").lower()
        (preferred if any(name in kind for name in ("cpu", "x86_pkg", "package", "k10")) else fallback).append(value)
    values = preferred or fallback
    return round(max(values)) if values else None


class Sampler:
    def __init__(self):
        self.cpu = {}
        self.net = {}
        self.at = None
        self.tools = {name: bool(shutil.which(name)) for name in ("btop", "ncdu")}

    def snapshot(self):
        at = time.monotonic()
        ticks = cpu_ticks(read("/proc/stat"))
        usage = cpu_usage(self.cpu, ticks)
        counters = net_counters(read("/proc/net/dev"))
        routes = [line.split() for line in read("/proc/net/route").splitlines()[1:]]
        interface = next((row[0] for row in routes if len(row) > 3 and row[1] == "00000000" and row[0] in counters), "")
        if not interface:
            interface = next((name for name in counters if read(Path("/sys/class/net") / name / "operstate").strip() == "up"), "")
        rates = [None, None]
        if interface and interface in self.net and self.at is not None and at > self.at:
            rates = [max(0, counters[interface][index] - self.net[interface][index]) / (at - self.at) for index in (0, 1)]
        self.cpu, self.net, self.at = ticks, counters, at
        try:
            disk = os.statvfs(Path.home())
            storage = {"total": disk.f_blocks * disk.f_frsize, "free": disk.f_bavail * disk.f_frsize}
        except OSError:
            storage = {"total": 0, "free": 0}
        running = re.search(r"^procs_running\s+(\d+)", read("/proc/stat"), re.MULTILINE)
        result = {"cpu": usage.get("cpu"), "cores": [usage[name] for name in sorted(usage) if name != "cpu"],
                  "memory": memory(read("/proc/meminfo")), "storage": storage, "temperature": temperature(),
                  "network": {"interface": interface, "rx": rates[0], "tx": rates[1]},
                  "processes": sum(entry.name.isdigit() for entry in Path("/proc").iterdir()),
                  "running": int(running[1]) if running else 0, "audio": audio_state(), "tools": self.tools}
        quiet = command(["omarchy-shell", "notifications", "dndState"])
        wifi = command(["nmcli", "radio", "wifi"])
        result["quiet"] = quiet == "on" if quiet in {"on", "off"} else None
        result["wifi"] = wifi == "enabled" if wifi in {"enabled", "disabled"} else None
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--volume", type=int)
    parser.add_argument("--mute", action="store_true")
    args = parser.parse_args()
    if args.volume is not None:
        if not 0 <= args.volume <= 100:
            parser.error("Volume must be between 0 and 100")
        subprocess.run(["pactl", "set-sink-volume", audio_sink(), f"{args.volume}%"], check=True)
        return
    if args.mute:
        subprocess.run(["pactl", "set-sink-mute", audio_sink(), "toggle"], check=True)
        return
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    sampler = Sampler()
    while not stop.is_set():
        snapshot = sampler.snapshot()
        if stop.is_set():
            break
        try:
            print(json.dumps(snapshot), flush=True)
        except BrokenPipeError:
            break
        if not args.watch or stop.wait(2.5):
            break


if __name__ == "__main__":
    main()
