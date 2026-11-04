#!/usr/bin/env python3
"""Check the release version or bump manifest/changelog together; never publish."""
import argparse
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def bumped(version, part):
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise ValueError("Expected a numeric semantic version: MAJOR.MINOR.PATCH")
    numbers = list(map(int, version.split(".")))
    index = {"major": 0, "minor": 1, "patch": 2}[part]
    numbers[index] += 1
    numbers[index + 1:] = [0] * (2 - index)
    return ".".join(map(str, numbers))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "major", "minor", "patch"])
    parser.add_argument("note", nargs="?", help="One release-note sentence (required for a bump)")
    args = parser.parse_args()
    manifest_path = ROOT / "manifest.json"
    changelog_path = ROOT / "CHANGELOG.md"
    manifest = json.loads(manifest_path.read_text())
    current = manifest["version"]
    bumped(current, "patch")  # Validate even when checking without a bump.
    changelog = changelog_path.read_text()
    releases = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    if not releases or releases[0] != current:
        parser.error("The first changelog release must match manifest.json")
    if args.action == "check":
        status = "unreleased development; last release " if "\n## [Unreleased]" in changelog else "release "
        print(f"{manifest['id']} {current} ({status}v{current})")
        return
    if not args.note or "\n" in args.note or "\r" in args.note:
        parser.error("Provide one single-line release-note sentence")
    version = bumped(current, args.action)
    heading = changelog.index("\n## [")
    updated = changelog[:heading] + f"\n## [{version}] - {date.today().isoformat()}\n\n- {args.note}\n" + changelog[heading:]
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    changelog_path.write_text(updated)
    print(f"{current} -> {version}; review, test and commit before tagging v{version}.")


if __name__ == "__main__":
    main()
