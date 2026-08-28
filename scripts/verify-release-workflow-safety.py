#!/usr/bin/env python3
"""Executable, adversarial release-publication safety matrix."""
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
REPOSITORY = "https://github.com/backstop-ai/backstop-design-system.git"
TAG = "v0.1.5"
LOG_PATHS = [
    "release-evidence/logs/pack-check.log",
    "release-evidence/logs/pack-test.log",
    "release-evidence/logs/public-site-acceptance.log",
    "release-evidence/logs/canonical-wordmark-v015-candidate.log",
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
    "TestCanonicalWordmarkV015_AcceptsExactVisibleOwnerByDispatch",
    "TestCanonicalWordmarkV015_RejectsPrefixedOwnerMarkerByDispatch",
    "TestCanonicalWordmarkV015_RejectsOwnerAndComponentConcealmentByDispatch",
    "TestCanonicalWordmarkV015_ReviewCorrectionChangeFence",
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
    "TestReleaseClassifier_DerivesCandidatePackageContentHash",
    "TestReleaseClassifier_RejectsForgedStaleAndMissingContentHashBindings",
    "TestReleaseClassifier_RejectsForgedStaleAndMissingLogEvidenceBindings",
    "TestReleaseWorkflow_AdversarialContentHashAndLogBindings",
    "TestReleaseWorkflow_AdversarialCommandsResultsAndRefs",
    "TestReleaseWorkflow_AdversarialParentsSequenceAndCommitIdentities",
    "TestReleaseWorkflow_AdversarialTagCandidateAcceptanceOwnerAndEventIdentities",
    "TestReleaseWorkflow_ExecutesExtractedProductionTrustedLauncher",
    "TestReleaseWorkflow_MandatedCasesAreDistinctAndSubstantive",
    "TestReleaseWorkflow_PreTagRunsBackstopGateAll",
    "TestReleaseWorkflow_CompleteCandidateKillChainPrecedesTagMutation",
]
CHECKS = {
    "pack-check": ("backstop pack check .", LOG_PATHS[0]),
    "pack-test": ("backstop pack test .", LOG_PATHS[1]),
    "public-site-acceptance": ("python3 scripts/verify-public-site-acceptance.py", LOG_PATHS[2]),
    "canonical-wordmark-v015-candidate": ("python3 scripts/verify-canonical-wordmark-v015.py --candidate --base v0.1.4", LOG_PATHS[3]),
    "release-workflow-safety": ("python3 scripts/verify-release-workflow-safety.py", LOG_PATHS[4]),
}
SCENARIOS: list[str] = []
CLASSIFIER_EXECUTIONS = 0


def expected_logs() -> dict[str, bytes]:
    return {
        LOG_PATHS[0]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[1]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase3-fixtures: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[2]: b"public-site-acceptance: PASS\n",
        LOG_PATHS[3]: b"".join(f"PASS {name}\n".encode() for name in CANONICAL_NAMES),
        LOG_PATHS[4]: b"".join(f"PASS {name}\n".encode() for name in WORKFLOW_NAMES),
    }


def parsed_workflow() -> dict:
    value = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    assert isinstance(value, dict) and isinstance(value.get("jobs"), dict)
    return value


def steps() -> list[dict]:
    value = parsed_workflow()["jobs"]["publish"]["steps"]
    assert isinstance(value, list)
    return value


def run_block(name: str) -> str:
    return next(str(step["run"]) for step in steps() if step.get("name") == name)


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False, env=env)
    if result.returncode:
        raise AssertionError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def write(repo: Path, relative: str, data: bytes) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def commit(repo: Path, message: str, *, name: str = BOT_NAME, email: str = BOT_EMAIL,
           extra_env: dict[str, str] | None = None) -> str:
    environment = os.environ | {
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
    } | (extra_env or {})
    git(repo, "commit", "-q", "-m", message, env=environment)
    return git(repo, "rev-parse", "HEAD")


def candidate_content_hash(repo: Path, commit_sha: str) -> str:
    paths = git(repo, "ls-tree", "-r", "--name-only", commit_sha).splitlines()
    rows = []
    for relative in sorted(paths):
        data = subprocess.run(["git", "show", f"{commit_sha}:{relative}"], cwd=repo,
                              capture_output=True, check=True).stdout
        rows.append(f"{relative}:{hashlib.sha256(data).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def history() -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temporary = tempfile.TemporaryDirectory()
    repo = Path(temporary.name)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Fixture User")
    git(repo, "config", "user.email", "fixture@example.invalid")
    write(repo, "pack.yml", b'name: backstop-ai/backstop-design-system\nversion: "0.1.5"\n')
    write(repo, "scripts/classify-release-publication.py", CLASSIFIER.read_bytes())
    write(repo, "bundles/BUNDLE-001-design-system-release.bundle.md", b"owner\n")
    write(repo, "contracts/public-site-acceptance.yml", b"acceptance\n")
    write(repo, "assets/design-system-tokens.css", b"tokens\n")
    for relative, data in expected_logs().items():
        write(repo, relative, data if relative not in LOG_PATHS[-2:] else b"stale tagged output\n")
    git(repo, "add", ".")
    candidate = commit(repo, "candidate", name="Fixture User", email="fixture@example.invalid")
    git(repo, "tag", TAG, candidate)
    return temporary, repo, candidate


def add_authentic_logs(repo: Path) -> str:
    for relative, data in expected_logs().items():
        write(repo, relative, data)
    git(repo, "add", *LOG_PATHS)
    result = commit(repo, f"Record {TAG} publication checks")
    changed = set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", result).splitlines())
    assert changed == set(LOG_PATHS[-2:]), "byte-identical inherited logs were artificially changed"
    return result


def evidence_document(repo: Path, candidate: str, log_commit: str) -> dict:
    content_hash = candidate_content_hash(repo, candidate)
    checks = []
    for name, (command, relative) in CHECKS.items():
        data = subprocess.run(["git", "show", f"{log_commit}:{relative}"], cwd=repo,
                              capture_output=True, check=True).stdout
        checks.append({"check": name, "command": command, "exit_code": 0, "result": "pass",
                       "subject_commit": candidate, "subject_content_hash": content_hash,
                       "log_ref": {"repository": REPOSITORY, "commit": log_commit,
                                   "path": relative, "sha256": hashlib.sha256(data).hexdigest()}})
    return {
        "schema_version": "website-pack-release-evidence/v1",
        "subject": {"role": "design-system", "manifest_identity": "backstop-ai/backstop-design-system",
                    "source_coordinate": "backstop-ai/backstop-design-system", "version": "0.1.5",
                    "git_ref": TAG, "release_commit": candidate, "content_hash": content_hash},
        "owner_artifact": {"repository": REPOSITORY, "commit": candidate,
                           "path": "bundles/BUNDLE-001-design-system-release.bundle.md",
                           "sha256": hashlib.sha256(b"owner\n").hexdigest()},
        "public_site_acceptance": {
            "schema_version": "backstop-design-system/public-site-acceptance/v1",
            "subject_commit": candidate, "subject_content_hash": content_hash,
            "export": {"path": "contracts/public-site-acceptance.yml",
                       "sha256": hashlib.sha256(b"acceptance\n").hexdigest()},
            "token_asset": {"path": "assets/design-system-tokens.css", "media_type": "text/css",
                            "sha256": hashlib.sha256(b"tokens\n").hexdigest()}},
        "common_checks": checks, "documentation_semantics": None,
    }


def add_evidence(repo: Path, candidate: str, log_commit: str, *, mutate=None,
                 name: str = BOT_NAME, email: str = BOT_EMAIL) -> str:
    evidence = evidence_document(repo, candidate, log_commit)
    if mutate:
        mutate(evidence)
    path = f"release-evidence/{TAG}.yml"
    write(repo, path, yaml.safe_dump(evidence, sort_keys=False).encode())
    git(repo, "add", path)
    return commit(repo, f"Publish {TAG} release evidence", name=name, email=email)


def classify(repo: Path, candidate: str, *, actor: str = BOT_NAME, automatic: bool = True,
             classifier: Path = CLASSIFIER, branch: str = "main", conclusion: str = "success") -> subprocess.CompletedProcess[str]:
    global CLASSIFIER_EXECUTIONS
    CLASSIFIER_EXECUTIONS += 1
    args = [sys.executable, str(classifier), "--repo", str(repo), "--tag", TAG,
            "--candidate-sha", candidate, "--event-name", "workflow_run" if automatic else "workflow_dispatch",
            "--actor", actor]
    if automatic:
        args += ["--workflow-run-head-sha", candidate, "--workflow-run-head-branch", branch,
                 "--workflow-run-conclusion", conclusion]
    return subprocess.run(args, text=True, capture_output=True, check=False)


def assert_fatal(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode != 0 and "fatal-mismatch" in result.stderr, result.stdout + result.stderr
    assert reason in result.stderr, f"expected {reason!r}, got {result.stderr!r}"


def valid_publication() -> tuple[tempfile.TemporaryDirectory[str], Path, str, str, str]:
    temporary, repo, candidate = history()
    log_commit = add_authentic_logs(repo)
    evidence_commit = add_evidence(repo, candidate, log_commit)
    return temporary, repo, candidate, log_commit, evidence_commit


def mutation_case(label: str, mutate, reason: str) -> None:
    SCENARIOS.append(label)
    temporary, repo, candidate = history()
    try:
        log_commit = add_authentic_logs(repo)
        evidence_commit = add_evidence(repo, candidate, log_commit, mutate=mutate)
        assert_fatal(classify(repo, evidence_commit), reason)
    finally:
        temporary.cleanup()


def test_no_head_fallback() -> None:
    runs = "\n".join(str(step.get("run", "")) for step in steps())
    assert "github.event.workflow_run.head_sha" in WORKFLOW.read_text()
    assert "CANDIDATE_SHA=$(git rev-parse HEAD)" not in runs


def test_mismatch() -> None:
    temporary, repo, _ = history()
    try:
        write(repo, "new.txt", b"new\n"); git(repo, "add", "new.txt")
        new = commit(repo, "new", name="Fixture User", email="fixture@example.invalid")
        assert_fatal(classify(repo, new), "publication commit identity or message mismatch")
    finally: temporary.cleanup()


def test_evidence() -> None:
    temporary, repo, _, _, evidence_commit = valid_publication()
    try:
        result = classify(repo, evidence_commit)
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
    finally: temporary.cleanup()


def test_resume() -> None:
    temporary, repo, candidate = history()
    try:
        result = classify(repo, candidate, actor="human")
        assert result.returncode == 0 and result.stdout.strip() == "resume-same-candidate"
    finally: temporary.cleanup()


def test_order() -> None:
    text = WORKFLOW.read_text()
    assert text.index("backstop pack check .") < text.index('git tag "$TAG"')


def test_manual_sha() -> None:
    assert parsed_workflow()["on"]["workflow_dispatch"]["inputs"]["candidate_sha"]["required"] == "true"


def test_commands() -> None:
    template = yaml.safe_load((ROOT / "release-evidence/template.yml").read_text())
    commands = {entry["check"]: entry["command"] for entry in template["common_checks"]}
    assert "./bin/backstop" not in str(commands)
    assert commands.get("canonical-wordmark-v015-candidate") == CHECKS["canonical-wordmark-v015-candidate"][0]


def test_two_changed() -> None:
    temporary, repo, _ = history()
    try:
        descendant = add_authentic_logs(repo)
        result = classify(repo, descendant)
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
    finally: temporary.cleanup()


def test_subsets() -> None:
    temporary, repo, _ = history()
    try:
        write(repo, LOG_PATHS[0], expected_logs()[LOG_PATHS[0]] + b"forged\n")
        git(repo, "add", LOG_PATHS[0]); descendant = commit(repo, f"Record {TAG} publication checks")
        assert_fatal(classify(repo, descendant), "required publication output mismatch")
    finally: temporary.cleanup()


def test_mismatch_matrix() -> None:
    for label, kwargs, reason in [
        ("actor", {"actor": "attacker"}, "existing tag points"),
        ("branch", {"branch": "dev"}, "metadata does not bind"),
        ("conclusion", {"conclusion": "failure"}, "metadata does not bind")]:
        SCENARIOS.append("historical-" + label)
        temporary, repo, _ = history()
        try:
            descendant = add_authentic_logs(repo)
            assert_fatal(classify(repo, descendant, **kwargs), reason)
        finally: temporary.cleanup()


def test_regression_matrix() -> None:
    test_two_changed(); test_subsets(); test_mismatch_matrix()


def test_trusted_launcher() -> None:
    resolve = run_block("Resolve immutable candidate and publication mode")
    assert "git show" in resolve and "CLASSIFIER_BLOB" in resolve


def test_derives_content_hash() -> None:
    assert candidate_content_hash(ROOT, "v0.1.4") == "e7abab70123b6bef7ed3835f2e7d9f451850f3a2981e04729aa29354be2e871d"
    temporary, repo, _, _, evidence_commit = valid_publication()
    try:
        result = classify(repo, evidence_commit)
        assert result.returncode == 0 and result.stdout.strip() == "post-tag-noop", result.stderr
    finally: temporary.cleanup()


def test_rejects_content_bindings() -> None:
    for label, mutate, reason in [
        ("content-forged", lambda e: [e["subject"].__setitem__("content_hash", "a"*64), e["public_site_acceptance"].__setitem__("subject_content_hash", "a"*64), [c.__setitem__("subject_content_hash", "a"*64) for c in e["common_checks"]]], "does not match immutable candidate bytes"),
        ("content-stale", lambda e: e["subject"].__setitem__("content_hash", "0"*64), "does not match immutable candidate bytes"),
        ("content-malformed", lambda e: e["subject"].__setitem__("content_hash", "xyz"), "content hash is malformed"),
        ("content-missing", lambda e: e["subject"].pop("content_hash"), "subject fields mismatch"),
    ]: mutation_case(label, mutate, reason)


def test_rejects_log_evidence_bindings() -> None:
    for label, mutate, reason in [
        ("log-hash-forged", lambda e: e["common_checks"][0]["log_ref"].__setitem__("sha256", "a"*64), "log hash mismatch"),
        ("log-commit-disconnected", lambda e: e["common_checks"][0]["log_ref"].__setitem__("commit", e["subject"]["release_commit"]), "log-ref binding mismatch"),
        ("log-path-missing", lambda e: e["common_checks"][0]["log_ref"].__setitem__("path", "release-evidence/logs/missing.log"), "log-ref binding mismatch"),
    ]: mutation_case(label, mutate, reason)


def test_adversarial_content_logs() -> None:
    mutation_case("matrix-content-cross-check", lambda e: e["common_checks"][2].__setitem__("subject_content_hash", "f"*64), "check binding mismatch")
    mutation_case("matrix-log-cross-check", lambda e: e["common_checks"][2]["log_ref"].__setitem__("sha256", "f"*64), "log hash mismatch")


def test_adversarial_commands_refs() -> None:
    mutation_case("command", lambda e: e["common_checks"][0].__setitem__("command", "true"), "check binding mismatch")
    mutation_case("result", lambda e: e["common_checks"][1].__setitem__("result", "fail"), "check binding mismatch")
    mutation_case("order", lambda e: e["common_checks"].reverse(), "missing, extra, or reordered")
    mutation_case("ref-repository", lambda e: e["common_checks"][3]["log_ref"].__setitem__("repository", "https://example.invalid/x"), "log-ref binding mismatch")


def test_adversarial_commit_identities() -> None:
    SCENARIOS.append("log-author")
    temporary, repo, _ = history()
    try:
        for relative, data in expected_logs().items(): write(repo, relative, data)
        git(repo, "add", *LOG_PATHS)
        descendant = commit(repo, f"Record {TAG} publication checks", name="attacker", email="attacker@example.invalid")
        assert_fatal(classify(repo, descendant), "publication commit identity or message mismatch")
    finally: temporary.cleanup()
    SCENARIOS.append("evidence-author")
    temporary, repo, candidate = history()
    try:
        log_commit = add_authentic_logs(repo)
        evidence_commit = add_evidence(repo, candidate, log_commit, name="attacker", email="attacker@example.invalid")
        assert_fatal(classify(repo, evidence_commit), "publication commit identity or message mismatch")
    finally: temporary.cleanup()


def test_adversarial_release_identities() -> None:
    mutation_case("subject-tag", lambda e: e["subject"].__setitem__("git_ref", "v9.9.9"), "tag/candidate identity mismatch")
    mutation_case("owner-commit", lambda e: e["owner_artifact"].__setitem__("commit", "0"*40), "owner binding mismatch")
    mutation_case("acceptance-commit", lambda e: e["public_site_acceptance"].__setitem__("subject_commit", "0"*40), "acceptance identity mismatch")
    test_mismatch_matrix()


def execute_resolve_block() -> None:
    SCENARIOS.append("production-resolve-block")
    temporary, repo, _ = history()
    try:
        descendant = add_authentic_logs(repo)
        malicious = b'#!/usr/bin/env python3\nfrom pathlib import Path\nPath("SENTINEL").write_text("executed")\nprint("post-tag-noop")\n'
        write(repo, "scripts/classify-release-publication.py", malicious)
        git(repo, "add", "scripts/classify-release-publication.py")
        descendant = commit(repo, "replace authenticator")
        git(repo, "remote", "add", "origin", ".")
        runner = repo / "runner"; runner.mkdir()
        env = os.environ | {"EVENT_NAME": "workflow_run", "EVENT_ACTOR": BOT_NAME,
            "AUTOMATIC_SHA": descendant, "AUTOMATIC_BRANCH": "main", "AUTOMATIC_CONCLUSION": "success",
            "MANUAL_SHA": "", "RUNNER_TEMP": str(runner), "GITHUB_ENV": str(repo/"github-env"),
            "GITHUB_OUTPUT": str(repo/"github-output")}
        result = subprocess.run(["bash", "-c", run_block("Resolve immutable candidate and publication mode")],
                                cwd=repo, env=env, text=True, capture_output=True, check=False)
        assert result.returncode != 0 and not (repo / "SENTINEL").exists(), result.stdout + result.stderr
        trusted = runner / f"trusted-classifier-{TAG}.py"
        assert trusted.is_file() and trusted.read_bytes() == subprocess.run(
            ["git", "show", f"{TAG}:scripts/classify-release-publication.py"], cwd=repo,
            capture_output=True, check=True).stdout
    finally: temporary.cleanup()


def test_extracted_launcher() -> None:
    execute_resolve_block()


def test_distinct_cases() -> None:
    functions = [test_adversarial_content_logs, test_adversarial_commands_refs,
                 test_adversarial_commit_identities, test_adversarial_release_identities,
                 test_extracted_launcher]
    assert len(set(functions)) == len(functions), "mandated tests alias function objects"
    before = CLASSIFIER_EXECUTIONS
    labels_before = len(SCENARIOS)
    for function in functions[:-1]: function()
    new_labels = SCENARIOS[labels_before:]
    assert CLASSIFIER_EXECUTIONS > before and new_labels
    assert len(new_labels) == len(set(new_labels)), "duplicate mutation scenarios detected"


def shim_repository(fail_token: str = "") -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, str], Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name); repo = root / "repo"; remote = root / "remote.git"; runner = root / "runner"
    repo.mkdir(); runner.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Fixture User"); git(repo, "config", "user.email", "fixture@example.invalid")
    for relative in ["pack.yml", "issues/ISSUE-003-v015-independent-review-corrections.issue.md",
                     "plans/PLAN-ISSUE-003-v015-independent-review-corrections.plan.yml"]:
        write(repo, relative, b"fixture\n")
    git(repo, "add", "."); candidate = commit(repo, "candidate", name="Fixture User", email="fixture@example.invalid")
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote)); git(repo, "push", "-q", "-u", "origin", "main")
    bin_dir = root / "bin"; bin_dir.mkdir(); trace = root / "trace"
    shim = """#!/bin/sh
printf '%s|%s\\n' "$PWD" "$*" >> "$TRACE"
if [ -n "$FAIL_TOKEN" ]; then
  case "$*" in *"$FAIL_TOKEN"*) exit 23;; esac
fi
exit 0
"""
    write(bin_dir, "backstop", shim.encode()); write(bin_dir, "python3", shim.encode())
    os.chmod(bin_dir / "backstop", 0o755); os.chmod(bin_dir / "python3", 0o755)
    env = os.environ | {"PATH": f"{bin_dir}:{os.environ['PATH']}", "TRACE": str(trace),
        "FAIL_TOKEN": fail_token, "RUNNER_TEMP": str(runner), "CANDIDATE_SHA": candidate, "TAG": TAG}
    return temporary, repo, env, trace


def execute_pre_tag(fail_token: str = "", create_tag: bool = False):
    temporary, repo, env, trace = shim_repository(fail_token)
    proof = subprocess.run(["bash", "-c", run_block("Prove detached candidate and capture exact logs")],
                           cwd=repo, env=env, text=True, capture_output=True, check=False)
    tag_result = None
    if proof.returncode == 0 and create_tag:
        tag_result = subprocess.run(["bash", "-c", run_block("Preserve or create immutable candidate tag")],
                                    cwd=repo, env=env, text=True, capture_output=True, check=False)
    return temporary, repo, env, trace, proof, tag_result


def test_pre_tag_gate_all() -> None:
    temporary, _, _, trace, result, _ = execute_pre_tag()
    try:
        assert result.returncode == 0, result.stdout + result.stderr
        lines = trace.read_text().splitlines()
        assert any(line.endswith("backstop gate --all") or line.endswith("gate --all") for line in lines), lines
    finally: temporary.cleanup()


def test_complete_pre_tag_chain() -> None:
    expected = ["artifact validate --issue ISSUE-003", "artifact validate --plan PLAN-ISSUE-003",
                "gate --all", "pack check .", "pack test .", "verify-public-site-acceptance.py",
                "verify-canonical-wordmark-v015.py --candidate --base v0.1.4", "verify-release-workflow-safety.py"]
    temporary, repo, _, trace, proof, tag_result = execute_pre_tag(create_tag=True)
    try:
        assert proof.returncode == 0 and tag_result and tag_result.returncode == 0, proof.stderr + (tag_result.stderr if tag_result else "")
        actual = trace.read_text().splitlines()
        positions = [next(i for i, line in enumerate(actual) if token in line) for token in expected]
        assert positions == sorted(positions) and git(repo, "rev-parse", f"{TAG}^{{commit}}")
    finally: temporary.cleanup()
    for token in expected:
        temporary, repo, _, _, proof, tag_result = execute_pre_tag(token, create_tag=True)
        try:
            assert proof.returncode != 0 and tag_result is None
            assert not subprocess.run(["git", "rev-parse", "--verify", TAG], cwd=repo, capture_output=True).returncode == 0
        finally: temporary.cleanup()


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
    "TestReleaseClassifier_DerivesCandidatePackageContentHash": test_derives_content_hash,
    "TestReleaseClassifier_RejectsForgedStaleAndMissingContentHashBindings": test_rejects_content_bindings,
    "TestReleaseClassifier_RejectsForgedStaleAndMissingLogEvidenceBindings": test_rejects_log_evidence_bindings,
    "TestReleaseWorkflow_AdversarialContentHashAndLogBindings": test_adversarial_content_logs,
    "TestReleaseWorkflow_AdversarialCommandsResultsAndRefs": test_adversarial_commands_refs,
    "TestReleaseWorkflow_AdversarialParentsSequenceAndCommitIdentities": test_adversarial_commit_identities,
    "TestReleaseWorkflow_AdversarialTagCandidateAcceptanceOwnerAndEventIdentities": test_adversarial_release_identities,
    "TestReleaseWorkflow_ExecutesExtractedProductionTrustedLauncher": test_extracted_launcher,
    "TestReleaseWorkflow_MandatedCasesAreDistinctAndSubstantive": test_distinct_cases,
    "TestReleaseWorkflow_PreTagRunsBackstopGateAll": test_pre_tag_gate_all,
    "TestReleaseWorkflow_CompleteCandidateKillChainPrecedesTagMutation": test_complete_pre_tag_chain,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus", choices=["classifier", "launcher", "pre-tag"])
    args = parser.parse_args()
    if args.focus == "classifier":
        selected = WORKFLOW_NAMES[14:17]
    elif args.focus == "launcher":
        selected = ["TestReleaseWorkflow_ExecutesExtractedProductionTrustedLauncher"]
    elif args.focus == "pre-tag":
        selected = WORKFLOW_NAMES[-2:]
    else:
        selected = list(TESTS)
    failures = 0
    for name in selected:
        try:
            TESTS[name]()
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError, TypeError, StopIteration,
                subprocess.CalledProcessError, yaml.YAMLError) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
