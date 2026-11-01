"""Read desktop-entry icon metadata for the configured workspace shortcuts."""
import configparser
import json
import os
from pathlib import Path
import subprocess


def command(args):
    env = dict(os.environ)
    env.pop("BROWSER", None)
    try:
        return subprocess.run(args, env=env, capture_output=True, text=True, timeout=2, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def metadata(desktop):
    desktop = desktop.split(":", 1)[0]
    if not desktop or Path(desktop).name != desktop:
        return {}
    home = Path.home()
    locations = [Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")), home / ".nix-profile/share"]
    locations += [Path(path) for path in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if path]
    for location in locations:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(location / "applications" / desktop)
            entry = parser["Desktop Entry"]
            return {"desktop": desktop, "name": entry.get("Name", ""), "icon": entry.get("Icon", "")}
        except (OSError, configparser.Error, KeyError):
            continue
    return {}


def workspace_icons():
    try:
        editor = (Path.home() / ".local/state/omarchy/defaults/editor").read_text().strip()
    except OSError:
        editor = "nvim"
    editor_ids = {"nvim": "nvim.desktop", "vim": "vim.desktop", "nano": "nano.desktop", "micro": "micro.desktop",
                  "hx": "Helix.desktop", "helix": "Helix.desktop", "code": "code.desktop", "cursor": "cursor.desktop",
                  "zeditor": "dev.zed.Zed.desktop", "zed": "dev.zed.Zed.desktop", "subl": "sublime_text.desktop"}
    executable = Path(editor).name
    browser = command(["xdg-settings", "get", "default-web-browser"]) or command(["xdg-mime", "query", "default", "x-scheme-handler/https"])
    return {"editor": metadata(editor_ids.get(executable, executable + ".desktop")),
            "terminal": metadata(command(["xdg-terminal-exec", "--print-id"])),
            "browser": metadata(browser),
            "files": metadata(command(["xdg-mime", "query", "default", "inode/directory"])),
            "notes": metadata("obsidian.desktop") or metadata("md.obsidian.Obsidian.desktop")}


if __name__ == "__main__":
    print(json.dumps(workspace_icons()))
