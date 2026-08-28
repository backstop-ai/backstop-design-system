#!/usr/bin/env python3
"""Independent post-publication proof; never part of the candidate gate."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = "TestReleaseV013_WordmarkIdentityAndEvidenceAreBound"
COMMANDS = {
    "pack-check": "backstop pack check .",
    "pack-test": "backstop pack test .",
    "public-site-acceptance": "python3 scripts/verify-public-site-acceptance.py",
    "canonical-wordmark-v013-candidate": "python3 scripts/verify-canonical-wordmark-v013.py --candidate --base v0.1.2",
    "release-workflow-safety": "python3 scripts/verify-release-workflow-safety.py",
}


def git(*args: str, text: bool = True):
    result = subprocess.run(["git", *args], cwd=ROOT, text=text, capture_output=True, check=False)
    if result.returncode:
        error = result.stderr.strip() if text else result.stderr.decode().strip()
        raise AssertionError(error)
    return result.stdout.strip() if text else result.stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--evidence-commit", required=True)
    args = parser.parse_args()
    try:
        assert git("rev-parse", f"{args.tag}^{{commit}}") == args.candidate_sha, "tag does not bind candidate"
        assert git("merge-base", "--is-ancestor", args.candidate_sha, args.evidence_commit) == ""
        evidence_path = f"release-evidence/{args.tag}.yml"
        evidence = yaml.safe_load(git("show", f"{args.evidence_commit}:{evidence_path}"))
        subject = evidence["subject"]
        assert subject["git_ref"] == args.tag and subject["release_commit"] == args.candidate_sha
        assert subject["version"] == args.tag.removeprefix("v")

        owner = evidence["owner_artifact"]
        assert owner["commit"] == args.candidate_sha
        assert owner["sha256"] == sha(git("show", f"{args.candidate_sha}:{owner['path']}", text=False))
        acceptance = evidence["public_site_acceptance"]
        assert acceptance["subject_commit"] == args.candidate_sha
        assert acceptance["export"]["sha256"] == sha(git("show", f"{args.candidate_sha}:{acceptance['export']['path']}", text=False))
        assert acceptance["token_asset"]["sha256"] == sha(git("show", f"{args.candidate_sha}:{acceptance['token_asset']['path']}", text=False))

        checks = evidence["common_checks"]
        assert {check["check"] for check in checks} == set(COMMANDS)
        for check in checks:
            name = check["check"]
            assert check["command"] == COMMANDS[name]
            assert check["exit_code"] == 0 and check["result"] == "pass"
            assert check["subject_commit"] == args.candidate_sha
            assert check["subject_content_hash"] == subject["content_hash"]
            ref = check["log_ref"]
            log_bytes = git("show", f"{ref['commit']}:{ref['path']}", text=False)
            assert ref["sha256"] == sha(log_bytes)
            assert git("merge-base", "--is-ancestor", args.candidate_sha, ref["commit"]) == ""
            if name == "canonical-wordmark-v013-candidate":
                assert log_bytes.count(b"PASS Test") == 8 and b"FAIL Test" not in log_bytes
            if name == "release-workflow-safety":
                assert log_bytes.count(b"PASS Test") == 7 and b"FAIL Test" not in log_bytes

        with tempfile.TemporaryDirectory() as directory:
            consumer = Path(directory)
            (consumer / "backstop.yml").write_text("project: release-proof\npacks: {}\n", encoding="utf-8")
            result = subprocess.run(
                ["backstop", "pack", "add", f"backstop-ai/backstop-design-system@{subject['version']}"],
                cwd=consumer, text=True, capture_output=True, check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            lock = yaml.safe_load((consumer / "backstop.lock").read_text(encoding="utf-8"))
            serialized = str(lock)
            assert subject["content_hash"] in serialized, "resolved lock does not contain evidence content hash"

        print(f"PASS {NAME}")
        return 0
    except (AssertionError, KeyError, FileNotFoundError, TypeError, yaml.YAMLError) as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
