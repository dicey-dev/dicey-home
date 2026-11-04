"""Development deployment tests use temporary folders and mocked shell IPC."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("development", ROOT / "scripts/dev.py")
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)
PLUGIN_ID = json.loads((ROOT / "manifest.json").read_text())["id"]


class DevelopmentTest(unittest.TestCase):
    def test_recovery_does_not_require_a_working_source_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "omarchy/development"
            state.mkdir(parents=True)
            journal = state / (PLUGIN_ID + ".json")
            journal.write_text(json.dumps({"previous": PLUGIN_ID}))
            with patch.dict(os.environ, {"XDG_STATE_HOME": directory, "XDG_CONFIG_HOME": directory}), \
                 patch.object(dev, "ROOT", Path(directory) / "missing-source"), \
                 patch.object(sys, "argv", ["dev.py", "restore"]), patch.object(dev, "listed", return_value=[]), \
                 patch.object(dev, "command"), patch.object(dev, "rescan_until"):
                dev.main()
            self.assertFalse(journal.exists())

    def test_runtime_snapshot_excludes_tooling_and_scopes_development_id(self):
        files = dev.snapshot(ROOT)
        self.assertIn(Path("home/qmldir"), files)
        self.assertFalse(any(set(path.parts) & dev.EXCLUDED for path in files))
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            dev.write_stage(files, stage, PLUGIN_ID)
            self.assertEqual(json.loads((stage / "manifest.json").read_text())["id"], PLUGIN_ID + ".dev")
            for path in stage.rglob("*.qml"):
                self.assertNotIn('"' + PLUGIN_ID + '"', path.read_text())

    def test_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "linked.qml").symlink_to(ROOT / "manifest.json")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                dev.snapshot(root)

    def test_invalid_update_preserves_previous_development_and_production(self):
        files = dev.snapshot(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            plugins = Path(directory)
            production = plugins / PLUGIN_ID
            production.mkdir()
            (production / "sentinel").write_text("stable")
            with patch.object(dev, "command"):
                dev.deploy(files, plugins, PLUGIN_ID)
            target = plugins / (PLUGIN_ID + ".dev")
            before = (target / "manifest.json").read_bytes()
            with patch.object(dev, "command", side_effect=subprocess.CalledProcessError(1, "validate")):
                with self.assertRaises(subprocess.CalledProcessError):
                    dev.deploy(files, plugins, PLUGIN_ID)
            self.assertEqual((target / "manifest.json").read_bytes(), before)
            self.assertEqual((production / "sentinel").read_text(), "stable")

    def test_unmanaged_development_folder_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            plugins = Path(directory)
            (plugins / (PLUGIN_ID + ".dev")).mkdir()
            with self.assertRaisesRegex(ValueError, "unmanaged"):
                dev.deploy(dev.snapshot(ROOT), plugins, PLUGIN_ID)

    def test_start_restores_previous_activation_on_interrupt(self):
        kind = "bar" if PLUGIN_ID == "dicey.bar" else "menu"
        rows = [{"id": PLUGIN_ID, "kinds": [kind], "enabled": True}]
        active = [{"id": PLUGIN_ID + ".dev", "kinds": [kind], "enabled": True}]
        with tempfile.TemporaryDirectory() as directory:
            env = {"XDG_CONFIG_HOME": directory + "/config", "XDG_STATE_HOME": directory + "/state"}
            with patch.dict(os.environ, env), patch.object(sys, "argv", ["dev.py", "start"]), \
                 patch.object(dev, "listed", side_effect=[rows, active]), \
                 patch.object(dev, "command") as command, patch.object(dev, "rescan_until"), patch.object(dev.signal, "signal"), \
                 patch.object(dev.time, "sleep", side_effect=KeyboardInterrupt):
                dev.main()
            calls = [call.args for call in command.call_args_list]
            self.assertIn(("omarchy", "plugin", "enable", PLUGIN_ID + ".dev"), calls)
            self.assertIn(("omarchy", "plugin", "disable", PLUGIN_ID + ".dev"), calls)
            self.assertIn(("omarchy", "plugin", "enable", PLUGIN_ID), calls)
            self.assertFalse((Path(env["XDG_CONFIG_HOME"]) / "omarchy/plugins" / (PLUGIN_ID + ".dev")).exists())
            self.assertFalse((Path(env["XDG_STATE_HOME"]) / "omarchy/development" / (PLUGIN_ID + ".json")).exists())

    def test_failed_restore_keeps_recovery_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "session.json"
            journal.write_text(json.dumps({"previous": PLUGIN_ID}))
            with patch.object(dev, "listed", return_value=[]), \
                 patch.object(dev, "command", side_effect=subprocess.CalledProcessError(1, "enable")):
                with self.assertRaises(subprocess.CalledProcessError):
                    dev.restore(journal, Path(directory), PLUGIN_ID)
            self.assertTrue(journal.exists())
