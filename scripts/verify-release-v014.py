#!/usr/bin/env python3
"""Independent v0.1.4 publication proof; its output is never release evidence."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
V013 = "cb35c69e89844c5955d51b1b10e67da938010039"
NAMES = [
    "TestReleaseV014_ClassifierFixAndEvidenceAreBound",
    "TestReleaseV014_PreservesCanonicalWordmarkContract",
    "TestReleaseV014_PreservesV013TagIdentity",
]


def git(*args: str, text: bool = True):
    result = subprocess.run(["git", *args], cwd=ROOT, text=text, capture_output=True, check=False)
    if result.returncode:
        error = result.stderr.strip() if text else result.stderr.decode().strip()
        raise AssertionError(error)
    return result.stdout.strip() if text else result.stdout


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v0.1.4")
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--evidence-commit", required=True)
    args = parser.parse_args()
    failures: dict[str, str] = {}
    evidence = None
    try:
        assert git("rev-parse", f"{args.tag}^{{commit}}") == args.candidate_sha, "v0.1.4 tag does not bind candidate"
        assert args.candidate_sha != V013 and len(args.candidate_sha) == 40
        assert git("rev-list", "--parents", "-n", "1", args.evidence_commit).split()[1:] and len(git("rev-list", "--parents", "-n", "1", args.evidence_commit).split()[1:]) == 1
        evidence = yaml.safe_load(git("show", f"{args.evidence_commit}:release-evidence/{args.tag}.yml"))
        subject = evidence["subject"]
        assert subject["git_ref"] == args.tag and subject["release_commit"] == args.candidate_sha
        assert subject["version"] == "0.1.4" and len(subject["content_hash"]) == 64
        checks = evidence["common_checks"]
        expected = yaml.safe_load(git("show", f"{args.candidate_sha}:release-evidence/template.yml"))["common_checks"]
        assert [item["check"] for item in checks] == [item["check"] for item in expected]
        log_commits = {item["log_ref"]["commit"] for item in checks}
        assert len(log_commits) == 1
        log_commit = next(iter(log_commits))
        assert git("rev-parse", f"{args.evidence_commit}^") == log_commit
        assert git("rev-parse", f"{log_commit}^") == args.candidate_sha
        for item, template in zip(checks, expected):
            assert item["command"] == template["command"] and item["exit_code"] == 0 and item["result"] == "pass"
            assert item["subject_commit"] == args.candidate_sha and item["subject_content_hash"] == subject["content_hash"]
            ref = item["log_ref"]
            assert ref["sha256"] == digest(git("show", f"{ref['commit']}:{ref['path']}", text=False))
        with tempfile.TemporaryDirectory() as directory:
            consumer = Path(directory)
            (consumer / "backstop.yml").write_text("project: release-proof\npacks: {}\n", encoding="utf-8")
            result = subprocess.run(
                ["backstop", "pack", "add", "backstop-ai/backstop-design-system@0.1.4"],
                cwd=consumer, text=True, capture_output=True, check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            lock = yaml.safe_load((consumer / "backstop.lock").read_text(encoding="utf-8"))
            assert subject["content_hash"] in str(lock), "resolved tagged pack hash differs from evidence"
    except (AssertionError, KeyError, TypeError, yaml.YAMLError) as exc:
        failures[NAMES[0]] = str(exc)
    try:
        pack = yaml.safe_load(git("show", f"{args.candidate_sha}:pack.yml"))
        assert pack["version"] == "0.1.4" and pack["content"]["ruleset"]["version"] == "1.3.0"
        assert len(pack["content"]["ruleset"]["rules"]) == 7
        owner = git("show", f"{args.candidate_sha}:fixtures/rules/valid/index.html", text=False)
        assert owner.count(b'<a data-backstop-wordmark href="/"><span>./b</span><span>backstop</span><span>.sh</span></a>') == 1
        canonical_log = next(item for item in evidence["common_checks"] if item["check"] == "canonical-wordmark-v013-candidate")
        output = git("show", f"{canonical_log['log_ref']['commit']}:{canonical_log['log_ref']['path']}", text=False)
        assert output.count(b"PASS Test") == 8 and b"FAIL Test" not in output
    except (AssertionError, KeyError, TypeError) as exc:
        failures[NAMES[1]] = str(exc)
    try:
        assert git("rev-parse", "v0.1.3^{commit}") == V013
        remote = git("ls-remote", "--tags", "origin", "refs/tags/v0.1.3").split()[0]
        assert remote == V013, "remote v0.1.3 moved"
    except (AssertionError, IndexError) as exc:
        failures[NAMES[2]] = str(exc)
    for name in NAMES:
        print(f"FAIL {name}: {failures[name]}" if name in failures else f"PASS {name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
