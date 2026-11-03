#!/usr/bin/env python3
"""Opt-in development deployment; never write the production plugin folder."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "dicey.home"
KIND = "menu"
EXCLUDED = {".git", ".dev", ".venv", ".serena", ".opencode", "__pycache__",
            "docs", "tests", "scripts", "mockups", "preview", "node_modules"}
MARKER = ".dicey-development"


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def snapshot(root):
    """Read runtime files only; reject symlinks rather than follow them."""
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith("."))
        for name in dirs + names:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"Symlink is not allowed: {path}")
        for name in sorted(names):
            path = Path(directory) / name
            if not name.startswith(".") and (path.suffix in {".qml", ".js", ".py", ".json"} or name == "LICENSE"):
                files[path.relative_to(root)] = path.read_bytes()
    return files


def write_stage(files, stage, plugin_id):
    dev_id = plugin_id + ".dev"
    for relative, data in files.items():
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Scope literal IPC/state IDs in the development copy, not the source.
        if relative.suffix in {".qml", ".js", ".py", ".json"}:
            data = data.decode().replace(plugin_id, dev_id).encode()
        destination.write_bytes(data)
    manifest_path = stage / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["id"] = dev_id
    if isinstance(manifest.get("name"), str):
        manifest["name"] += " (development)"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (stage / MARKER).write_text(plugin_id + "\n")


def require_owned(target, plugin_id):
    if target.is_symlink() or not (target / MARKER).is_file() or (target / MARKER).read_text() != plugin_id + "\n":
        raise ValueError(f"Refusing to replace an unmanaged development folder: {target}")


def deploy(files, plugins, plugin_id):
    target = plugins / (plugin_id + ".dev")
    plugins.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        require_owned(target, plugin_id)
    with tempfile.TemporaryDirectory(prefix=".dicey-stage-", dir=plugins) as directory:
        stage = Path(directory) / "plugin"
        stage.mkdir()
        write_stage(files, stage, plugin_id)
        command("omarchy", "plugin", "validate", str(stage))
        old = Path(directory) / "previous"
        if target.exists():
            target.rename(old)
        try:
            stage.rename(target)
        except OSError:
            if old.exists():
                old.rename(target)
            raise
    command("omarchy-shell", "shell", "rescanPlugins")


def listed():
    return json.loads(command("omarchy", "plugin", "list", "--json"))


def rescan_until(plugin_id, present):
    # rescanPlugins returns before the shell's manifest subprocess finishes.
    deadline = time.monotonic() + 10
    while True:
        command("omarchy-shell", "shell", "rescanPlugins")
        if any(row["id"] == plugin_id for row in listed()) == present:
            return
        if time.monotonic() >= deadline:
            raise ValueError(f"Shell discovery did not settle for {plugin_id}")
        time.sleep(0.1)


def restore(journal, plugins, plugin_id):
    if not journal.exists():
        raise ValueError("No development session to restore.")
    previous = json.loads(journal.read_text())["previous"]
    dev_id = plugin_id + ".dev"
    target = plugins / dev_id
    if target.exists() or target.is_symlink():
        require_owned(target, plugin_id)
    if any(row["id"] == dev_id and row["enabled"] for row in listed()):
        command("omarchy", "plugin", "disable", dev_id)
    command("omarchy", "plugin", "enable", previous)
    if target.exists():
        shutil.rmtree(target)
    rescan_until(dev_id, False)
    journal.unlink()
    print(f"Restored {previous}; production files were not modified.", flush=True)


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "restore"])
    args = parser.parse_args()
    # Recovery must work even while the source manifest is broken or missing.
    plugin_id = PLUGIN_ID
    kind = KIND
    plugins = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy/plugins"
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy/development"
    state.mkdir(parents=True, exist_ok=True)
    journal = state / (plugin_id + ".json")
    with (state / (plugin_id + ".lock")).open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, "Development is already running. Stop it with Ctrl+C in its terminal.\n")
        if args.action == "restore":
            restore(journal, plugins, plugin_id)
            return
        if journal.exists():
            parser.exit(1, "An interrupted session exists. Run scripts/dev.py restore first.\n")
        target = plugins / (plugin_id + ".dev")
        if target.exists() or target.is_symlink():
            parser.exit(1, f"Development folder already exists; inspect it before continuing: {target}\n")
        previous = [row["id"] for row in listed() if kind in row["kinds"] and row["enabled"]]
        if len(previous) != 1:
            parser.exit(1, f"Expected one enabled {kind}; found {previous}. No activation changed.\n")
        files = snapshot(ROOT)
        journal.write_text(json.dumps({"previous": previous[0]}) + "\n")
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        try:
            deploy(files, plugins, plugin_id)
            rescan_until(plugin_id + ".dev", True)
            if kind == "menu":
                command("omarchy", "plugin", "disable", previous[0])
            command("omarchy", "plugin", "enable", plugin_id + ".dev")
            print(f"Development active: {plugin_id}.dev from {ROOT}\nCtrl+C restores {previous[0]}.", flush=True)
            while True:
                time.sleep(0.5)
                try:
                    changed = snapshot(ROOT)
                    if changed != files:
                        deploy(changed, plugins, plugin_id)
                        files = changed
                        print("Development copy updated.", flush=True)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    print(f"Update rejected; fix the source and save again: {getattr(error, 'stderr', None) or error}", flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            # Keep the journal on failure so restore can be retried, including
            # after a shell crash or an uncatchable termination.
            restore(journal, plugins, plugin_id)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(getattr(error, "stderr", None) or str(error))
