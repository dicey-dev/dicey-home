"""Resolve the default browser's search setting without reading browsing history.

Chromium-family preferences and the selected engine's Web Data row are read-only.
Firefox-family searches are delegated to the browser's native --search command.
No provider is substituted when a browser setting cannot be resolved.
"""

import configparser
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import urllib.parse


class SearchSettingError(ValueError):
    pass


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def default_desktop():
    env = dict(os.environ)
    env.pop("BROWSER", None)  # Match omarchy launch browser, not shell overrides.
    for args in (("xdg-settings", "get", "default-web-browser"),
                 ("xdg-mime", "query", "default", "x-scheme-handler/https")):
        try:
            desktop = subprocess.run(args, env=env, capture_output=True, text=True,
                                     timeout=2, check=True).stdout.strip()
            if desktop and Path(desktop).name == desktop:
                return desktop
        except (OSError, subprocess.SubprocessError):
            pass
    raise SearchSettingError("No default browser is configured")


def desktop_entry(desktop, home):
    data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    locations = [data_home, home / ".nix-profile/share"]
    locations += [Path(path) for path in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if path]
    for location in locations:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(location / "applications" / desktop)
            entry = parser["Desktop Entry"]
            return entry.get("Name", desktop), shlex.split(entry.get("Exec", ""))
        except (OSError, ValueError, KeyError, configparser.Error):
            continue
    raise SearchSettingError("The default browser's desktop entry could not be read")


def chromium_directory(identity, config):
    # Ordered to distinguish Chrome/Edge release channels and Brave from Chrome.
    for names, directory in (
        (("brave",), "BraveSoftware/Brave-Browser"),
        (("vivaldi-snapshot",), "vivaldi-snapshot"),
        (("vivaldi",), "vivaldi"),
        (("microsoft-edge-dev", "msedge-dev"), "microsoft-edge-dev"),
        (("microsoft-edge-beta", "msedge-beta"), "microsoft-edge-beta"),
        (("microsoft-edge", "msedge"), "microsoft-edge"),
        (("chrome-unstable",), "google-chrome-unstable"),
        (("chrome-beta",), "google-chrome-beta"),
        (("google-chrome",), "google-chrome"),
        (("chromium",), "chromium"),
    ):
        if any(name in identity for name in names):
            return config / directory
    return None


def preference_engine(preferences):
    for key in ("default_search_provider_data", "default_search_provider"):
        provider = preferences.get(key)
        if not isinstance(provider, dict):
            continue
        if provider.get("enabled") is False:
            raise SearchSettingError("Search is disabled by the browser configuration")
        engine = provider.get("template_url_data", provider)
        if isinstance(engine, dict) and (engine.get("url") or engine.get("search_url")):
            return engine
    return None


def database_engine(path):
    if not path.is_file():
        return None
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2)) as database:
            row = database.execute("SELECT value FROM meta WHERE key = ?", ("Default Search Provider ID",)).fetchone()
            if not row:
                return None
            database.row_factory = sqlite3.Row
            engine = database.execute("SELECT short_name, url FROM keywords WHERE id = ?", (row[0],)).fetchone()
            return dict(engine) if engine else None
    except sqlite3.Error:
        return None


def search_url(template, query):
    # Chromium's Google templates include browser-only optional parameters.
    # Resolve their base URL and remove optional tokens, retaining the actual
    # engine's URL rather than substituting a generic provider.
    template = template.replace("{google:baseURL}", "https://www.google.com/")
    template = template.replace("{google:baseSearchURL}", "https://www.google.com/")
    template = template.replace("{inputEncoding}", "UTF-8").replace("{outputEncoding}", "UTF-8")
    template = template.replace("{language}", "en")
    marker = "{searchTerms}" if "{searchTerms}" in template else "{searchTerms?}" if "{searchTerms?}" in template else "%s"
    if marker not in template:
        raise SearchSettingError("The browser engine does not expose a supported search URL")
    template = re.sub(r"\{google:[^}]+\}|\{[^}]+\?\}",
                      lambda match: match[0] if match[0] == marker else "", template)
    url = template.replace(marker, urllib.parse.quote_plus(query))
    parsed = urllib.parse.urlsplit(url)
    if "{" in url or "}" in url or parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise SearchSettingError("The browser's search URL is unsupported")
    return url


def resolve():
    home = Path.home()
    desktop = default_desktop()
    browser, arguments = desktop_entry(desktop, home)
    identity = (desktop + " " + (Path(arguments[0]).name if arguments else "")).lower()
    if any(name in identity for name in ("firefox", "librewolf", "floorp", "zen-browser", "zen_browser", "zen.desktop")):
        return {"browser": browser, "name": "Browser default", "mode": "native", "desktop": desktop}
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    directory = chromium_directory(identity, config)
    if directory is None:
        raise SearchSettingError("This browser's search setting is not supported yet")
    # Omarchy invokes the desktop entry's executable, without its arguments.
    # Its normal browser profile is therefore Local State's last-used profile.
    local = read_json(directory / "Local State")
    profile_name = local.get("profile", {}).get("last_used", "Default")
    if not isinstance(profile_name, str) or Path(profile_name).name != profile_name:
        raise SearchSettingError("The browser's selected profile is invalid")
    profile = directory / profile_name
    engine = None
    for file in ("Secure Preferences", "Preferences"):
        engine = preference_engine(read_json(profile / file))
        if engine:
            break
    engine = engine or database_engine(profile / "Web Data")
    if not engine:
        raise SearchSettingError("The browser's default search engine could not be determined")
    template = engine.get("url") or engine.get("search_url")
    search_url(template, "validation")
    return {"browser": browser, "name": str(engine.get("short_name") or engine.get("name") or "Browser default"),
            "mode": "url", "desktop": desktop, "template": template, "profile": str(profile)}


def describe(engine=None):
    try:
        engine = engine or resolve()
        key = hashlib.sha256(json.dumps(engine, sort_keys=True).encode()).hexdigest()[:20]
        return {"browser": engine["browser"], "name": engine["name"], "mode": engine["mode"], "key": key, "ready": True}
    except (SearchSettingError, OSError, ValueError) as error:
        return {"browser": "Default browser", "name": "Browser default", "mode": "unavailable", "key": "", "ready": False, "error": str(error)}


def open_search(query):
    engine = resolve()  # Re-read at activation, even if a preview was cached.
    arguments = ["--search", query] if engine["mode"] == "native" else [search_url(engine["template"], query)]
    subprocess.Popen(["omarchy", "launch", "browser", *arguments], start_new_session=True)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--describe":
        print(json.dumps(describe()))
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--open":
        try:
            open_search(sys.argv[2])
        except (SearchSettingError, OSError, ValueError) as error:
            subprocess.run(["notify-send", "Launcher web search", str(error)], check=False)
            raise SystemExit(1)
        return
    raise SystemExit("Usage: browser_search.py --describe | --open QUERY")


if __name__ == "__main__":
    main()
