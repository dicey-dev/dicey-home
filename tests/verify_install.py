"""Real Omarchy install/update/remove filesystem test, with desktop IPC stubbed.

Requires Git and Omarchy on PATH. Uses only a temporary HOME and local Git
source; never enables/disables a plugin in the running desktop.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, env=None):
    return subprocess.run(args, env=env, check=True, capture_output=True, text=True, timeout=60).stdout


with tempfile.TemporaryDirectory(prefix="dicey-install-") as directory:
    work = Path(directory)
    source = work / "source"
    source.mkdir()
    names = run("git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    for name in names:
        path = ROOT / name
        if not name or not path.is_file():
            continue
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    run("git", "-C", str(source), "init", "-b", "main")

    def commit(note):
        run("git", "-C", str(source), "add", ".")
        run("git", "-C", str(source), "-c", "user.name=Plugin Test", "-c", "user.email=test@example.invalid", "commit", "-m", note)

    commit("Initial installation fixture")
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    plugin_id, repository = manifest["id"], manifest["url"] + ".git"
    home = work / "home"
    home.mkdir()
    tools = work / "bin"
    tools.mkdir()
    ipc = tools / "omarchy-shell"
    ipc.write_text("#!/usr/bin/env bash\nif [[ ${2:-} == listPlugins ]]; then printf '[]\\n'; else printf 'ok\\n'; fi\n")
    ipc.chmod(0o755)
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "PATH": str(tools) + os.pathsep + os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_COUNT": "2",
           "GIT_CONFIG_KEY_0": "url." + source.as_uri() + ".insteadOf", "GIT_CONFIG_VALUE_0": repository,
           "GIT_CONFIG_KEY_1": "protocol.file.allow", "GIT_CONFIG_VALUE_1": "always"}
    installed = home / ".config/omarchy/plugins" / plugin_id
    run("omarchy", "plugin", "add", repository, "--yes", env=env)
    assert (installed / ".git").is_dir()
    assert (installed / "THIRD_PARTY_NOTICES.md").is_file()
    initial_commit = run("git", "-C", str(installed), "rev-parse", "HEAD").strip()
    run("git", "-C", str(installed), "switch", "--detach", initial_commit)
    numbers = list(map(int, manifest["version"].split(".")))
    numbers[2] += 1
    manifest["version"] = ".".join(map(str, numbers))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    commit("Update fixture")
    run("omarchy", "plugin", "update", plugin_id, "--yes", env=env)
    assert json.loads((installed / "manifest.json").read_text())["version"] == manifest["version"]
    # Neither a named update nor update-all honors detached HEAD as a pin.
    run("git", "-C", str(installed), "switch", "--detach", initial_commit)
    run("omarchy", "plugin", "update", "--yes", env=env)
    assert json.loads((installed / "manifest.json").read_text())["version"] == manifest["version"]
    run("omarchy", "plugin", "remove", plugin_id, "--yes", env=env)
    assert not installed.exists()
    print(f"PASS {plugin_id}: official add/update/remove, isolated HOME, local Git, stubbed desktop IPC.")
