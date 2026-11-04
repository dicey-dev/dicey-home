import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_version", ROOT / "scripts/version.py")
version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version)


class ReleaseTest(unittest.TestCase):
    def test_semantic_bumps_and_invalid_versions(self):
        self.assertEqual(version.bumped("1.2.3", "patch"), "1.2.4")
        self.assertEqual(version.bumped("1.2.3", "minor"), "1.3.0")
        self.assertEqual(version.bumped("1.2.3", "major"), "2.0.0")
        for invalid in ("1.2", "01.2.3", "1.2.3-extra", "garbage"):
            with self.assertRaises(ValueError):
                version.bumped(invalid, "patch")

    def test_bump_updates_manifest_and_changelog_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"id": "example.test", "version": "1.2.3"}))
            (root / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.3]\n\n- Previous.\n")
            with patch.object(version, "ROOT", root), patch.object(sys, "argv", ["version.py", "minor", "A feature."]):
                version.main()
            self.assertEqual(json.loads((root / "manifest.json").read_text())["version"], "1.3.0")
            self.assertIn("\n## [1.3.0]", (root / "CHANGELOG.md").read_text())
            self.assertIn("\n## [1.2.3]", (root / "CHANGELOG.md").read_text())

    def test_distributed_license_and_release_metadata(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["license"], "Apache-2.0 AND MIT")
        self.assertTrue(manifest["url"].startswith("https://github.com/dicey-dev/"))
        self.assertIn("Copyright (c) David Heinemeier Hansson", (ROOT / "THIRD_PARTY_NOTICES.md").read_text())
        self.assertIn("Apache License", (ROOT / "LICENSE").read_text())
