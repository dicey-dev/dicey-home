import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / "activity.py"
spec = importlib.util.spec_from_file_location("control_activity", source)
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)


class ActivityTests(unittest.TestCase):
    def test_cpu_delta_ignores_guest_double_count_and_counts_iowait_as_idle(self):
        previous = activity.cpu_ticks("cpu 10 0 10 70 10 0 0 0 5 0\ncpu0 10 0 10 70 10 0 0 0 5 0")
        current = activity.cpu_ticks("cpu 20 0 20 140 20 0 0 0 15 0\ncpu0 20 0 20 140 20 0 0 0 15 0")
        self.assertEqual(activity.cpu_usage(previous, current), {"cpu": 20.0, "cpu0": 20.0})

    def test_first_sample_and_reset_are_unavailable(self):
        self.assertIsNone(activity.cpu_usage({}, {"cpu": (100, 80)})["cpu"])
        self.assertIsNone(activity.cpu_usage({"cpu": (100, 80)}, {"cpu": (90, 70)})["cpu"])

    def test_memory_uses_available_instead_of_only_free(self):
        values = activity.memory("MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 400 kB\nCached: 200 kB")
        self.assertEqual(values, {"total": 1024000, "used": 614400})

    def test_network_counters_ignore_loopback(self):
        counters = activity.net_counters("lo: 12 0 0 0 0 0 0 0 24 0 0 0 0 0 0 0\nwlan0: 1024 0 0 0 0 0 0 0 2048 0 0 0 0 0 0 0")
        self.assertEqual(counters, {"wlan0": (1024, 2048)})

    def test_output_snapshot_reads_the_resolved_physical_sink(self):
        outputs = ["physical-sink", "Volume: left: 40000 / 61% / 0 dB, right: 40000 / 61% / 0 dB", "Mute: yes"]
        with patch.object(activity, "command", side_effect=outputs) as command:
            snapshot = activity.audio_state()
        self.assertEqual(snapshot, {"available": True, "volume": 61, "muted": True, "sink": "physical-sink"})
        self.assertEqual(command.call_args_list[1].args[0], ["pactl", "get-sink-volume", "physical-sink"])

    def test_audio_action_resolves_the_sink_at_activation(self):
        with patch.object(activity, "audio_sink", return_value="new-output"), patch.object(activity.subprocess, "run") as run, \
                patch("sys.argv", ["activity.py", "--volume", "42"]):
            activity.main()
        self.assertEqual(run.call_args.args[0], ["pactl", "set-sink-volume", "new-output", "42%"])


if __name__ == "__main__":
    unittest.main()
