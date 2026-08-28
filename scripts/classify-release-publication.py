#!/usr/bin/env python3
"""Classify an immutable release candidate before publication side effects."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def changed_paths(repo: Path, commit: str) -> set[str]:
    return set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())


def is_log_commit(repo: Path, commit: str, tag_commit: str, tag: str) -> bool:
    expected = {
        "release-evidence/logs/pack-check.log", "release-evidence/logs/pack-test.log",
        "release-evidence/logs/public-site-acceptance.log",
        "release-evidence/logs/canonical-wordmark-v013-candidate.log",
        "release-evidence/logs/release-workflow-safety.log",
    }
    return (
        git(repo, "show", "-s", "--format=%an", commit) == "github-actions[bot]"
        and
        git(repo, "show", "-s", "--format=%s", commit) == f"Record {tag} publication checks"
        and git(repo, "rev-parse", f"{commit}^") == tag_commit
        and changed_paths(repo, commit) == expected
    )


def is_evidence_commit(repo: Path, commit: str, tag_commit: str, tag: str) -> bool:
    parent = git(repo, "rev-parse", f"{commit}^")
    evidence_path = f"release-evidence/{tag}.yml"
    if not (
        git(repo, "show", "-s", "--format=%s", commit) == f"Publish {tag} release evidence"
        and changed_paths(repo, commit) == {evidence_path}
        and is_log_commit(repo, parent, tag_commit, tag)
    ):
        return False
    evidence = yaml.safe_load(git(repo, "show", f"{commit}:{evidence_path}"))
    return isinstance(evidence, dict) and evidence.get("subject", {}).get("git_ref") == tag and evidence.get("subject", {}).get("release_commit") == tag_commit


def classify(args: argparse.Namespace) -> str:
    repo = Path(args.repo).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha):
        raise ValueError("candidate SHA must be a full lowercase commit SHA")
    if git(repo, "cat-file", "-t", args.candidate_sha) != "commit":
        raise ValueError("candidate SHA does not identify a commit")
    automatic = args.event_name == "workflow_run"
    if automatic:
        if (args.workflow_run_head_sha != args.candidate_sha or args.workflow_run_head_branch != "main" or args.workflow_run_conclusion != "success"):
            raise ValueError("workflow_run metadata does not bind the successful main candidate")
    elif args.event_name != "workflow_dispatch":
        raise ValueError("unsupported publication event")

    tag_ref = f"refs/tags/{args.tag}"
    if not git(repo, "rev-parse", "--verify", "--quiet", tag_ref, check=False):
        return "new-candidate"
    tag_commit = git(repo, "rev-parse", f"{tag_ref}^{{commit}}")
    if tag_commit == args.candidate_sha:
        return "resume-same-candidate"
    if not automatic or args.actor != "github-actions[bot]":
        raise ValueError("existing tag points at a different candidate")
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", tag_commit, args.candidate_sha], cwd=repo)
    if ancestry.returncode:
        raise ValueError("post-tag candidate is not a descendant of the tag")
    if is_log_commit(repo, args.candidate_sha, tag_commit, args.tag) or is_evidence_commit(repo, args.candidate_sha, tag_commit, args.tag):
        return "post-tag-noop"
    raise ValueError("existing tag differs and candidate is not an authentic publication descendant")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--actor", default="")
    parser.add_argument("--workflow-run-head-sha", default="")
    parser.add_argument("--workflow-run-head-branch", default="")
    parser.add_argument("--workflow-run-conclusion", default="")
    args = parser.parse_args()
    try:
        print(classify(args))
        return 0
    except (ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"fatal-mismatch: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
