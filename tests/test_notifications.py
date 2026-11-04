import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notifications


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.live = self.state / "notifications"
        self.history = self.live / "history"
        self.history.mkdir(parents=True)

    def entry(self, timestamp=100, identity=1, directory=None, **extra):
        value = {"timestamp": timestamp, "originalId": identity, "app": "Synthetic app",
                 "summary": "<b>literal</b>", "body": "Hello", "urgency": 1}
        value.update(extra)
        path = (directory or self.history) / f"{timestamp}-{identity}.json"
        path.write_text(json.dumps(value))
        return path

    def test_empty_first_run(self):
        self.assertEqual(notifications.snapshot(self.state)["rows"], [])
        self.assertTrue(notifications.snapshot(self.state)["ready"])

    def test_merge_order_dedup_and_allowlisted_fields(self):
        self.entry(execArgv='["evil"]', image="https://example.com/private")
        self.entry(directory=self.live, body="Live copy")
        self.entry(200, 2, urgency=2)
        result = notifications.snapshot(self.state)
        self.assertEqual([row["key"] for row in result["rows"]], ["200-2", "100-1"])
        self.assertTrue(result["rows"][1]["live"])
        self.assertEqual(result["rows"][1]["body"], "Live copy")
        self.assertNotIn("execArgv", result["rows"][1])
        self.assertNotIn("image", result["rows"][1])
        self.assertEqual(result["rows"][0]["summary"], "<b>literal</b>")

    def test_malformed_symlink_fifo_oversize_and_identity_are_skipped(self):
        self.entry().write_text("broken")
        self.entry(101).write_bytes(b"x" * (notifications.MAX_BYTES + 1))
        (self.history / "102-1.json").symlink_to(self.state / "outside.json")
        import os
        os.mkfifo(self.history / "103-1.json")
        self.entry(104, timestamp_override=1).write_text('{"timestamp":99,"originalId":1}')
        result = notifications.snapshot(self.state)
        self.assertTrue(result["warning"])
        self.assertEqual(result["rows"], [])

    def test_future_nan_negative_ids_and_bad_types(self):
        for index, value in enumerate([float("nan"), float("inf"), True, -1, "100", 10**16]):
            self.entry(index + 1).write_text(json.dumps({"timestamp": value, "originalId": 1}))
        self.entry(20, -1)
        self.assertEqual(notifications.snapshot(self.state)["rows"], [])

    def test_bounded_text_controls_and_unknown_app(self):
        self.entry(app=[], summary="A\u202e\x00B", body="x" * 8000, urgency="critical")
        row = notifications.snapshot(self.state)["rows"][0]
        self.assertEqual(row["app"], "Unknown app")
        self.assertEqual(row["summary"], "AB")
        self.assertEqual(len(row["body"]), 4096)
        self.assertEqual(row["urgency"], 1)

    def test_bounded_count_and_dnd(self):
        for index in range(8):
            self.entry(index + 1, index)
        (self.state / "notifications.json").write_text('{"dnd":true}')
        with patch.object(notifications, "MAX_FILES", 4):
            result = notifications.snapshot(self.state)
        self.assertEqual(len(result["rows"]), 4)
        self.assertEqual(result["rows"][0]["timestamp"], 8)
        self.assertTrue(result["warning"])
        self.assertTrue(result["dnd"])

    def test_read_error_is_not_a_successful_empty_feed(self):
        with patch.object(notifications.os, "scandir", side_effect=PermissionError):
            result = notifications.snapshot(self.state)
        self.assertFalse(result["ready"])
        self.assertTrue(result["error"])

    def test_reader_never_writes_history(self):
        path = self.entry()
        before = path.read_bytes()
        notifications.snapshot(self.state)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(len(list(self.history.iterdir())), 1)
