#!/usr/bin/env python3
"""Focused structural and executable safety assertions for publication."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release.yml"
CLASSIFIER = ROOT / "scripts/classify-release-publication.py"
LOG_PATHS = [
    "release-evidence/logs/pack-check.log", "release-evidence/logs/pack-test.log",
    "release-evidence/logs/public-site-acceptance.log",
    "release-evidence/logs/canonical-wordmark-v013-candidate.log",
    "release-evidence/logs/release-workflow-safety.log",
]


def parsed_workflow() -> dict:
    value = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(value, dict) and isinstance(value.get("jobs"), dict), "release workflow is not parsed structure"
    return value


def steps() -> list[dict]:
    value = parsed_workflow()["jobs"]["publish"]["steps"]
    assert isinstance(value, list), "publish steps are missing"
    return value


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def history() -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temporary = tempfile.TemporaryDirectory()
    repo = Path(temporary.name)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Fixture User")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "pack.yml").write_text('version: "0.1.3"\n', encoding="utf-8")
    git(repo, "add", "pack.yml")
    git(repo, "commit", "-q", "-m", "candidate")
    candidate = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "v0.1.3", candidate)
    return temporary, repo, candidate


def classify(repo: Path, candidate: str, *, actor: str = "human", automatic: bool = True) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CLASSIFIER), "--repo", str(repo), "--tag", "v0.1.3",
            "--candidate-sha", candidate, "--event-name", "workflow_run" if automatic else "workflow_dispatch",
            "--actor", actor]
    if automatic:
        args += ["--workflow-run-head-sha", candidate, "--workflow-run-head-branch", "main",
                 "--workflow-run-conclusion", "success"]
    return subprocess.run(args, text=True, capture_output=True, check=False)


def test_no_head_fallback() -> None:
    runs = "\n".join(str(step.get("run", "")) for step in steps())
    assert "github.event.workflow_run.head_sha" in WORKFLOW.read_text(encoding="utf-8")
    assert "CANDIDATE_SHA=$(git rev-parse HEAD)" not in runs and "OWNER_COMMIT=$(git rev-parse HEAD)" not in runs


def test_mismatch() -> None:
    temporary, repo, _tagged = history()
    try:
        (repo / "new.txt").write_text("new candidate\n", encoding="utf-8")
        git(repo, "add", "new.txt")
        git(repo, "commit", "-q", "-m", "genuine new candidate")
        result = classify(repo, git(repo, "rev-parse", "HEAD"))
        assert result.returncode != 0 and "fatal-mismatch" in result.stderr
    finally:
        temporary.cleanup()


def test_post_tag_noop() -> None:
    temporary, repo, _tagged = history()
    try:
        git(repo, "config", "user.name", "github-actions[bot]")
        git(repo, "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        for relative in LOG_PATHS:
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{relative}: PASS\n", encoding="utf-8")
        git(repo, "add", *LOG_PATHS)
        git(repo, "commit", "-q", "-m", "Record v0.1.3 publication checks")
        result = classify(repo, git(repo, "rev-parse", "HEAD"), actor="github-actions[bot]")
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
        guarded = [step for step in steps() if step.get("name") not in (None, "Resolve immutable candidate and publication mode")]
        assert all("post-tag-noop" in str(step.get("if", "")) for step in guarded if "uses" not in step or "checkout" not in str(step.get("uses"))), "post-tag no-op does not guard every later side effect"
    finally:
        temporary.cleanup()


def test_resume() -> None:
    temporary, repo, tagged = history()
    try:
        result = classify(repo, tagged)
        assert result.returncode == 0 and result.stdout.strip() == "resume-same-candidate", result.stderr
    finally:
        temporary.cleanup()


def test_order() -> None:
    entries = steps()
    proof_indexes = [index for index, step in enumerate(entries) if "backstop pack check ." in str(step.get("run", ""))]
    tag_indexes = [index for index, step in enumerate(entries) if 'git tag "$TAG"' in str(step.get("run", ""))]
    assert proof_indexes and tag_indexes and max(proof_indexes) < min(tag_indexes), "detached checks do not all precede tag creation"


def test_manual_sha() -> None:
    dispatch = parsed_workflow()["on"]["workflow_dispatch"]
    assert isinstance(dispatch, dict), "manual dispatch has no inputs"
    candidate = dispatch.get("inputs", {}).get("candidate_sha", {})
    assert candidate.get("required") == "true", "manual candidate_sha is not required"


def test_commands() -> None:
    template = yaml.safe_load((ROOT / "release-evidence/template.yml").read_text(encoding="utf-8"))
    commands = {entry["check"]: entry["command"] for entry in template["common_checks"]}
    assert all("./bin/backstop" not in command for command in commands.values())
    assert commands["pack-check"] == "backstop pack check ."
    assert commands["pack-test"] == "backstop pack test ."


TESTS = {
    "TestReleaseWorkflow_RejectsCurrentBranchHeadFallback": test_no_head_fallback,
    "TestReleaseWorkflow_RejectsMismatchedExistingTag": test_mismatch,
    "TestReleaseWorkflow_PostTagEvidenceDescendantIsTerminalNoOp": test_post_tag_noop,
    "TestReleaseWorkflow_SameCandidateTagIsResumable": test_resume,
    "TestReleaseWorkflow_ChecksPrecedeTagCreation": test_order,
    "TestReleaseWorkflow_RequiresManualCandidateSHA": test_manual_sha,
    "TestReleaseEvidence_RejectsFalseBinBackstopCommands": test_commands,
}


def main() -> int:
    failures = 0
    for name, check in TESTS.items():
        try:
            check()
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError, TypeError, subprocess.CalledProcessError) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
