import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notifications


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.store = self.state / "notifications"
        self.store.mkdir(parents=True)
        self.apps = Path(self.temp.name) / "applications"
        self.apps.mkdir()
        self.now = time.time()

    def row(self, key="nkey1", ts=None, **extra):
        value = {"key": key, "ts": self.now - 60 if ts is None else ts, "app": "Synthetic app",
                 "summary": "Hello", "body": "World", "source": "", "urgency": 1}
        value.update(extra)
        return value

    def write(self, name, rows):
        (self.store / name).write_text(json.dumps(rows))

    def snapshot(self, webapps=None):
        return notifications.snapshot(self.state, self.apps, webapps)

    def test_empty_first_run(self):
        result = self.snapshot()
        self.assertTrue(result["ready"])
        self.assertEqual(result["rows"], [])
        (self.store / "live.json").write_text("")
        self.assertTrue(self.snapshot()["ready"])

    def test_merge_order_live_wins_and_allowlisted_fields(self):
        self.write("history.json", [self.row("old", self.now - 120, execArgv='["evil"]', closed_ts=self.now),
                                    self.row("both", self.now - 30, body="Archived copy", closed_ts=self.now)])
        self.write("live.json", [self.row("both", self.now - 30, body="Live copy")])
        rows = self.snapshot()["rows"]
        self.assertEqual([row["key"] for row in rows], ["both", "old"])
        self.assertTrue(rows[0]["live"])
        self.assertEqual(rows[0]["body"], "Live copy")
        self.assertFalse(rows[1]["live"])
        self.assertNotIn("execArgv", rows[1])
        self.assertEqual(rows[1]["timestamp"], int((self.now - 120) * 1000))

    def test_groups_apps_sites_and_webapps(self):
        self.write("history.json", [
            self.row("a", app="Slack Desktop"),
            self.row("b", app="Chromium", source="www.example.com"),
            self.row("c", app="Firefox", source="web.whatsapp.com"),
            self.row("d", app="Google Chrome", source="Google Chrome"),  # Unlifted: stays the browser app.
            self.row("e", app="Chromium", source="127.0.0.1"),
            self.row("f", app="NotABrowser", source="example.com"),
        ])
        rows = {row["key"]: row for row in self.snapshot({"web.whatsapp.com": "WhatsApp"})["rows"]}
        self.assertEqual((rows["a"]["group"], rows["a"]["groupLabel"], rows["a"]["groupKind"], rows["a"]["browser"]),
                         ("app:slack-desktop", "Slack Desktop", "app", ""))
        self.assertEqual((rows["b"]["group"], rows["b"]["groupLabel"], rows["b"]["groupKind"], rows["b"]["browser"]),
                         ("site:www.example.com", "example.com", "site", "Chromium"))
        self.assertEqual((rows["c"]["group"], rows["c"]["groupLabel"], rows["c"]["groupKind"], rows["c"]["browser"]),
                         ("webapp:web.whatsapp.com", "WhatsApp", "webapp", "Firefox"))
        self.assertEqual(rows["d"]["group"], "app:google-chrome")
        self.assertEqual(rows["e"]["group"], "app:chromium")
        self.assertEqual(rows["f"]["group"], "app:notabrowser")

    def test_desktop_webapps(self):
        (self.apps / "WhatsApp.desktop").write_text(
            "[Desktop Entry]\nName=WhatsApp\nExec=omarchy-launch-webapp https://web.whatsapp.com/\n")
        (self.apps / "Chat.desktop").write_text(
            '[Desktop Entry]\nName=Chat\nExec=chromium --app="https://chat.example.org/x"\n')
        (self.apps / "Term.desktop").write_text("[Desktop Entry]\nName=Term\nExec=alacritty\n")
        (self.apps / "Bad.desktop").write_text("[Desktop Entry]\nName=Bad\nExec=omarchy-launch-webapp https://10.0.0.1/\n")
        (self.apps / "Big.desktop").write_bytes(b"x" * (notifications.MAX_DESKTOP_BYTES + 1))
        (self.apps / "Link.desktop").symlink_to(self.apps / "WhatsApp.desktop")
        self.assertEqual(notifications.desktop_webapps(self.apps),
                         {"web.whatsapp.com": "WhatsApp", "chat.example.org": "Chat"})
        self.assertEqual(notifications.desktop_webapps(self.apps / "missing"), {})

    def test_markup_is_reduced_to_text(self):
        self.write("history.json", [self.row(summary="<b>literal</b>", body="<b>Bold</b> &amp; <a href='x'>link</a><br/>next <3")])
        row = self.snapshot()["rows"][0]
        self.assertEqual(row["summary"], "<b>literal</b>")
        self.assertEqual(row["body"], "Bold & link\nnext <3")

    def test_invalid_identity_is_skipped_with_warning(self):
        self.write("history.json", [
            self.row("bad key"), self.row("x" * 121), self.row("future", self.now + 3600),
            self.row("nan", float("inf")), self.row("bool", True), self.row("neg", -1), self.row("str", "1"),
            "not an object", self.row("good"),
        ])
        result = self.snapshot()
        self.assertTrue(result["warning"])
        self.assertEqual([row["key"] for row in result["rows"]], ["good"])

    def test_malformed_symlink_and_oversize_files_are_not_ready(self):
        (self.store / "history.json").write_text("broken")
        self.assertFalse(self.snapshot()["ready"])
        (self.store / "history.json").write_text("{}")
        self.assertFalse(self.snapshot()["ready"])
        (self.store / "history.json").unlink()
        (self.store / "history.json").symlink_to(self.state / "outside.json")
        self.assertFalse(self.snapshot()["ready"])
        (self.store / "history.json").unlink()
        with patch.object(notifications, "MAX_BYTES", 8):
            self.write("history.json", [self.row()])
            result = self.snapshot()
        self.assertFalse(result["ready"])
        self.assertTrue(result["error"])

    def test_bounded_text_controls_and_unknown_app(self):
        self.write("history.json", [self.row(app=[], summary="A‮\x00B", body="x" * 8000, urgency="critical")])
        row = self.snapshot()["rows"][0]
        self.assertEqual(row["app"], "Unknown app")
        self.assertEqual(row["summary"], "AB")
        self.assertEqual(len(row["body"]), 4096)
        self.assertEqual(row["urgency"], 1)

    def test_bounded_count(self):
        self.write("history.json", [self.row(f"k{i}", self.now - i) for i in range(8)])
        with patch.object(notifications, "MAX_ROWS", 4):
            result = self.snapshot()
        self.assertEqual([row["key"] for row in result["rows"]], ["k0", "k1", "k2", "k3"])
        self.assertTrue(result["warning"])

    def test_read_error_is_not_a_successful_empty_feed(self):
        self.write("history.json", [self.row()])
        with patch.object(notifications.os, "open", side_effect=PermissionError):
            result = self.snapshot()
        self.assertFalse(result["ready"])
        self.assertTrue(result["error"])

    def test_reader_never_writes_host_state(self):
        self.write("history.json", [self.row()])
        before = {path.name: path.read_bytes() for path in self.store.iterdir()}
        self.snapshot()
        self.assertEqual({path.name: path.read_bytes() for path in self.store.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
