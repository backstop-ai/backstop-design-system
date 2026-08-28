#!/usr/bin/env python3
"""Executable release-publication safety matrix."""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release.yml"
CLASSIFIER = ROOT / "scripts/classify-release-publication.py"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
LOG_PATHS = [
    "release-evidence/logs/pack-check.log",
    "release-evidence/logs/pack-test.log",
    "release-evidence/logs/public-site-acceptance.log",
    "release-evidence/logs/canonical-wordmark-v013-candidate.log",
    "release-evidence/logs/release-workflow-safety.log",
]
CANONICAL_NAMES = [
    "TestCanonicalWordmark_AcceptsCompleteThreePartOwnerExactlyOnce",
    "TestCanonicalWordmark_RejectsTruncatedOwner",
    "TestCanonicalWordmark_RejectsSemanticDriftMatrix",
    "TestPackFixtures_AllClaimsRetainSubstantivePolarity",
    "TestCanonicalWordmark_RecipeSurfaceMatchesOwnerContract",
    "TestPublicSiteAcceptance_WordmarkMutationIsUniqueAndExact",
    "TestPublicSiteAcceptance_WordmarkMutationDispatchRejects",
    "TestCanonicalWordmarkV013_ChangeFence",
]
WORKFLOW_NAMES = [
    "TestReleaseWorkflow_RejectsCurrentBranchHeadFallback",
    "TestReleaseWorkflow_RejectsMismatchedExistingTag",
    "TestReleaseWorkflow_PostTagEvidenceDescendantIsTerminalNoOp",
    "TestReleaseWorkflow_SameCandidateTagIsResumable",
    "TestReleaseWorkflow_ChecksPrecedeTagCreation",
    "TestReleaseWorkflow_RequiresManualCandidateSHA",
    "TestReleaseEvidence_RejectsFalseBinBackstopCommands",
    "TestReleaseWorkflow_RegeneratedFiveLogsWithTwoChangedIsTerminalNoOp",
    "TestReleaseWorkflow_PostTagLogDescendantAllowsByteIdenticalOutputs",
    "TestReleaseWorkflow_PostTagEvidenceDescendantAuthenticatesRequiredOutputs",
    "TestReleaseWorkflow_RejectsArbitraryPublicationPathSubsets",
    "TestReleaseWorkflow_RejectsPublicationContentAndIdentityMismatch",
    "TestReleaseWorkflow_ClassifierRegressionMatrixRetainsPolarity",
    "TestReleaseWorkflow_ExistingTagUsesImmutableClassifierBytes",
]


def expected_logs() -> dict[str, bytes]:
    return {
        LOG_PATHS[0]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[1]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase3-fixtures: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[2]: b"public-site-acceptance: PASS\n",
        LOG_PATHS[3]: b"".join(f"PASS {name}\n".encode() for name in CANONICAL_NAMES),
        LOG_PATHS[4]: b"".join(f"PASS {name}\n".encode() for name in WORKFLOW_NAMES),
    }


def parsed_workflow() -> dict:
    value = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(value, dict) and isinstance(value.get("jobs"), dict), "release workflow is not parsed structure"
    return value


def steps() -> list[dict]:
    value = parsed_workflow()["jobs"]["publish"]["steps"]
    assert isinstance(value, list), "publish steps are missing"
    return value


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False, env=env)
    if result.returncode:
        raise AssertionError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def commit(repo: Path, message: str, *, name: str = BOT_NAME, email: str = BOT_EMAIL) -> str:
    environment = os.environ | {
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
    }
    git(repo, "commit", "-q", "-m", message, env=environment)
    return git(repo, "rev-parse", "HEAD")


def write(repo: Path, relative: str, data: bytes) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def history() -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temporary = tempfile.TemporaryDirectory()
    repo = Path(temporary.name)
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Fixture User")
    git(repo, "config", "user.email", "fixture@example.invalid")
    write(repo, "pack.yml", b'name: backstop-ai/backstop-design-system\nversion: "0.1.3"\n')
    write(repo, "scripts/classify-release-publication.py", CLASSIFIER.read_bytes())
    write(repo, "bundles/BUNDLE-001-design-system-release.bundle.md", b"owner\n")
    write(repo, "contracts/public-site-acceptance.yml", b"acceptance\n")
    write(repo, "assets/design-system-tokens.css", b"tokens\n")
    logs = expected_logs()
    for relative, data in logs.items():
        # The two changing outputs begin stale at the immutable candidate.
        write(repo, relative, data if relative not in LOG_PATHS[-2:] else b"stale tagged output\n")
    git(repo, "add", ".")
    commit(repo, "candidate", name="Fixture User", email="fixture@example.invalid")
    candidate = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "v0.1.3", candidate)
    return temporary, repo, candidate


def add_authentic_logs(repo: Path) -> str:
    for relative, data in expected_logs().items():
        write(repo, relative, data)
    git(repo, "add", *LOG_PATHS)
    descendant = commit(repo, "Record v0.1.3 publication checks")
    assert set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", descendant).splitlines()) == set(LOG_PATHS[-2:])
    for relative, data in expected_logs().items():
        actual = subprocess.run(["git", "show", f"{descendant}:{relative}"], cwd=repo, capture_output=True, check=True).stdout
        assert actual == data and hashlib.sha256(actual).digest() == hashlib.sha256(data).digest()
    return descendant


def classify(repo: Path, candidate: str, *, actor: str = BOT_NAME, automatic: bool = True,
             classifier: Path = CLASSIFIER, branch: str = "main", conclusion: str = "success") -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(classifier), "--repo", str(repo), "--tag", "v0.1.3",
            "--candidate-sha", candidate, "--event-name", "workflow_run" if automatic else "workflow_dispatch",
            "--actor", actor]
    if automatic:
        args += ["--workflow-run-head-sha", candidate, "--workflow-run-head-branch", branch,
                 "--workflow-run-conclusion", conclusion]
    return subprocess.run(args, text=True, capture_output=True, check=False)


def assert_fatal(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode != 0 and "fatal-mismatch" in result.stderr, result.stdout + result.stderr
    assert reason in result.stderr, f"expected {reason!r}, got {result.stderr!r}"


def test_no_head_fallback() -> None:
    runs = "\n".join(str(step.get("run", "")) for step in steps())
    assert "github.event.workflow_run.head_sha" in WORKFLOW.read_text(encoding="utf-8")
    assert "CANDIDATE_SHA=$(git rev-parse HEAD)" not in runs and "OWNER_COMMIT=$(git rev-parse HEAD)" not in runs


def test_mismatch() -> None:
    temporary, repo, _ = history()
    try:
        write(repo, "new.txt", b"new candidate\n")
        git(repo, "add", "new.txt")
        new = commit(repo, "genuine new candidate", name="Fixture User", email="fixture@example.invalid")
        assert_fatal(classify(repo, new), "publication commit identity or message mismatch")
    finally:
        temporary.cleanup()


def test_two_changed() -> None:
    temporary, repo, _ = history()
    try:
        descendant = add_authentic_logs(repo)
        result = classify(repo, descendant)
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
    finally:
        temporary.cleanup()


def test_evidence() -> None:
    temporary, repo, candidate = history()
    try:
        log_commit = add_authentic_logs(repo)
        checks = []
        commands = {
            "pack-check": "backstop pack check .", "pack-test": "backstop pack test .",
            "public-site-acceptance": "python3 scripts/verify-public-site-acceptance.py",
            "canonical-wordmark-v013-candidate": "python3 scripts/verify-canonical-wordmark-v013.py --candidate --base v0.1.3",
            "release-workflow-safety": "python3 scripts/verify-release-workflow-safety.py",
        }
        for name, relative in zip(commands, LOG_PATHS):
            checks.append({"check": name, "command": commands[name], "exit_code": 0, "result": "pass",
                           "subject_commit": candidate, "subject_content_hash": "a" * 64,
                           "log_ref": {"repository": "https://github.com/backstop-ai/backstop-design-system.git",
                                       "commit": log_commit, "path": relative,
                                       "sha256": hashlib.sha256(expected_logs()[relative]).hexdigest()}})
        evidence = {
            "schema_version": "website-pack-release-evidence/v1",
            "subject": {"role": "design-system", "manifest_identity": "backstop-ai/backstop-design-system",
                        "source_coordinate": "backstop-ai/backstop-design-system", "version": "0.1.3",
                        "git_ref": "v0.1.3", "release_commit": candidate, "content_hash": "a" * 64},
            "owner_artifact": {"repository": "https://github.com/backstop-ai/backstop-design-system.git",
                               "commit": candidate, "path": "bundles/BUNDLE-001-design-system-release.bundle.md",
                               "sha256": hashlib.sha256(b"owner\n").hexdigest()},
            "public_site_acceptance": {"schema_version": "backstop-design-system/public-site-acceptance/v1",
                                       "subject_commit": candidate, "subject_content_hash": "a" * 64,
                                       "export": {"path": "contracts/public-site-acceptance.yml", "sha256": hashlib.sha256(b"acceptance\n").hexdigest()},
                                       "token_asset": {"path": "assets/design-system-tokens.css", "media_type": "text/css", "sha256": hashlib.sha256(b"tokens\n").hexdigest()}},
            "common_checks": checks, "documentation_semantics": None,
        }
        path = "release-evidence/v0.1.3.yml"
        write(repo, path, yaml.safe_dump(evidence, sort_keys=False).encode())
        git(repo, "add", path)
        evidence_commit = commit(repo, "Publish v0.1.3 release evidence")
        result = classify(repo, evidence_commit)
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
    finally:
        temporary.cleanup()


def test_subsets() -> None:
    temporary, repo, _ = history()
    try:
        # An allowlisted one-path diff cannot hide a stale required output.
        write(repo, LOG_PATHS[0], expected_logs()[LOG_PATHS[0]] + b"forged\n")
        git(repo, "add", LOG_PATHS[0])
        one = commit(repo, "Record v0.1.3 publication checks")
        assert_fatal(classify(repo, one), "required publication output mismatch")
    finally:
        temporary.cleanup()


def test_mismatch_matrix() -> None:
    mutations = [
        ("actor", lambda repo, desc: classify(repo, desc, actor="attacker"), "existing tag points"),
        ("branch", lambda repo, desc: classify(repo, desc, branch="dev"), "metadata does not bind"),
        ("conclusion", lambda repo, desc: classify(repo, desc, conclusion="failure"), "metadata does not bind"),
    ]
    for _name, invoke, reason in mutations:
        temporary, repo, _ = history()
        try:
            desc = add_authentic_logs(repo)
            assert_fatal(invoke(repo, desc), reason)
        finally:
            temporary.cleanup()
    temporary, repo, _ = history()
    try:
        add_authentic_logs(repo)
        write(repo, "unexpected.txt", b"bad\n")
        git(repo, "add", "unexpected.txt")
        desc = commit(repo, "extra")
        assert_fatal(classify(repo, desc), "publication commit identity or message mismatch")
    finally:
        temporary.cleanup()


def test_regression_matrix() -> None:
    test_two_changed()
    test_subsets()
    test_mismatch_matrix()


def test_resume() -> None:
    temporary, repo, tagged = history()
    try:
        result = classify(repo, tagged, actor="human")
        assert result.returncode == 0 and result.stdout.strip() == "resume-same-candidate", result.stderr
    finally:
        temporary.cleanup()


def test_order() -> None:
    entries = steps()
    proof_indexes = [i for i, step in enumerate(entries) if "backstop pack check ." in str(step.get("run", ""))]
    tag_indexes = [i for i, step in enumerate(entries) if 'git tag "$TAG"' in str(step.get("run", ""))]
    assert proof_indexes and tag_indexes and max(proof_indexes) < min(tag_indexes), "detached checks do not all precede tag creation"


def test_manual_sha() -> None:
    candidate = parsed_workflow()["on"]["workflow_dispatch"].get("inputs", {}).get("candidate_sha", {})
    assert candidate.get("required") == "true", "manual candidate_sha is not required"


def test_commands() -> None:
    template = yaml.safe_load((ROOT / "release-evidence/template.yml").read_text(encoding="utf-8"))
    commands = {entry["check"]: entry["command"] for entry in template["common_checks"]}
    assert all("./bin/backstop" not in command for command in commands.values())
    assert commands["pack-check"] == "backstop pack check ." and commands["pack-test"] == "backstop pack test ."
    assert commands["canonical-wordmark-v013-candidate"] == "python3 scripts/verify-canonical-wordmark-v013.py --candidate --base v0.1.3"


def test_trusted_launcher() -> None:
    resolve = next(step["run"] for step in steps() if step.get("name") == "Resolve immutable candidate and publication mode")
    assert "git show" in resolve and "CLASSIFIER_BLOB" in resolve and "trusted-classifier" in resolve
    temporary, repo, _ = history()
    try:
        descendant = add_authentic_logs(repo)
        malicious = b'#!/usr/bin/env python3\nfrom pathlib import Path\nPath("SENTINEL").write_text("executed")\nprint("post-tag-noop")\n'
        write(repo, "scripts/classify-release-publication.py", malicious)
        git(repo, "add", "scripts/classify-release-publication.py")
        descendant = commit(repo, "replace authenticator")
        # Execute the same immutable extraction contract used by the production launcher.
        trusted = repo / "trusted-classifier.py"
        trusted.write_bytes(subprocess.run(["git", "show", "v0.1.3:scripts/classify-release-publication.py"], cwd=repo, capture_output=True, check=True).stdout)
        result = classify(repo, descendant, classifier=trusted)
        assert_fatal(result, "publication commit identity or message mismatch")
        assert not (repo / "SENTINEL").exists(), "descendant classifier executed"
    finally:
        temporary.cleanup()


TESTS = {
    "TestReleaseWorkflow_RejectsCurrentBranchHeadFallback": test_no_head_fallback,
    "TestReleaseWorkflow_RejectsMismatchedExistingTag": test_mismatch,
    "TestReleaseWorkflow_PostTagEvidenceDescendantIsTerminalNoOp": test_evidence,
    "TestReleaseWorkflow_SameCandidateTagIsResumable": test_resume,
    "TestReleaseWorkflow_ChecksPrecedeTagCreation": test_order,
    "TestReleaseWorkflow_RequiresManualCandidateSHA": test_manual_sha,
    "TestReleaseEvidence_RejectsFalseBinBackstopCommands": test_commands,
    "TestReleaseWorkflow_RegeneratedFiveLogsWithTwoChangedIsTerminalNoOp": test_two_changed,
    "TestReleaseWorkflow_PostTagLogDescendantAllowsByteIdenticalOutputs": test_two_changed,
    "TestReleaseWorkflow_PostTagEvidenceDescendantAuthenticatesRequiredOutputs": test_evidence,
    "TestReleaseWorkflow_RejectsArbitraryPublicationPathSubsets": test_subsets,
    "TestReleaseWorkflow_RejectsPublicationContentAndIdentityMismatch": test_mismatch_matrix,
    "TestReleaseWorkflow_ClassifierRegressionMatrixRetainsPolarity": test_regression_matrix,
    "TestReleaseWorkflow_ExistingTagUsesImmutableClassifierBytes": test_trusted_launcher,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus", choices=["classifier"])
    args = parser.parse_args()
    selected = list(TESTS)
    if args.focus:
        selected = [name for name in selected if name != "TestReleaseWorkflow_ExistingTagUsesImmutableClassifierBytes"]
    failures = 0
    for name in selected:
        try:
            TESTS[name]()
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError, TypeError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
