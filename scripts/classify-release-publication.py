#!/usr/bin/env python3
"""Classify publication from an immutable release contract."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
REPOSITORY = "https://github.com/backstop-ai/backstop-design-system.git"
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
CHECKS = {
    "pack-check": ("backstop pack check .", LOG_PATHS[0]),
    "pack-test": ("backstop pack test .", LOG_PATHS[1]),
    "public-site-acceptance": ("python3 scripts/verify-public-site-acceptance.py", LOG_PATHS[2]),
    "canonical-wordmark-v013-candidate": ("python3 scripts/verify-canonical-wordmark-v013.py --candidate --base v0.1.3", LOG_PATHS[3]),
    "release-workflow-safety": ("python3 scripts/verify-release-workflow-safety.py", LOG_PATHS[4]),
}


def expected_logs() -> dict[str, bytes]:
    return {
        LOG_PATHS[0]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[1]: b"status: pass\n- phase1-structural: pass\n- phase2-coherence: pass\n- phase3-fixtures: pass\n- phase4-archetype: pass\n- phase5-layer: pass\n- phase6-risk-class: pass\n",
        LOG_PATHS[2]: b"public-site-acceptance: PASS\n",
        LOG_PATHS[3]: b"".join(f"PASS {name}\n".encode() for name in CANONICAL_NAMES),
        LOG_PATHS[4]: b"".join(f"PASS {name}\n".encode() for name in WORKFLOW_NAMES),
    }


def git(repo: Path, *args: str, check: bool = True, text: bool = True):
    result = subprocess.run(["git", *args], cwd=repo, text=text, capture_output=True, check=False)
    if check and result.returncode:
        error = result.stderr.strip() if text else result.stderr.decode().strip()
        raise ValueError(error or f"git {' '.join(args)} failed")
    return (result.stdout.strip() if text else result.stdout) if result.returncode == 0 else ("" if text else b"")


def blob(repo: Path, commit: str, path: str) -> bytes:
    return git(repo, "show", f"{commit}:{path}", text=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parents(repo: Path, commit: str) -> list[str]:
    return git(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]


def changed_paths(repo: Path, commit: str) -> set[str]:
    return set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())


def authenticate_identity(repo: Path, commit: str, subject: str) -> None:
    fields = git(repo, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%s", commit).split("\0")
    if fields != [BOT_NAME, BOT_EMAIL, BOT_NAME, BOT_EMAIL, subject]:
        raise ValueError("publication commit identity or message mismatch")


def authenticate_logs(repo: Path, commit: str) -> None:
    for path, expected in expected_logs().items():
        try:
            actual = blob(repo, commit, path)
        except ValueError as exc:
            raise ValueError(f"required publication output missing: {path}") from exc
        if actual != expected or digest(actual) != digest(expected):
            raise ValueError(f"required publication output mismatch: {path}")


def is_log_commit(repo: Path, commit: str, tag_commit: str, tag: str) -> bool:
    if parents(repo, commit) != [tag_commit]:
        return False
    authenticate_identity(repo, commit, f"Record {tag} publication checks")
    changed = changed_paths(repo, commit)
    if not changed or not changed <= set(LOG_PATHS):
        raise ValueError("publication log commit changed an unexpected path")
    authenticate_logs(repo, commit)
    return True


def exact_mapping(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} fields mismatch")
    return value


def is_evidence_commit(repo: Path, commit: str, tag_commit: str, tag: str) -> bool:
    commit_parents = parents(repo, commit)
    if len(commit_parents) != 1:
        return False
    log_commit = commit_parents[0]
    if not is_log_commit(repo, log_commit, tag_commit, tag):
        return False
    authenticate_identity(repo, commit, f"Publish {tag} release evidence")
    evidence_path = f"release-evidence/{tag}.yml"
    if changed_paths(repo, commit) != {evidence_path}:
        raise ValueError("evidence commit must change exactly its versioned evidence path")
    try:
        evidence = yaml.safe_load(blob(repo, commit, evidence_path))
    except (ValueError, yaml.YAMLError) as exc:
        raise ValueError("release evidence is missing or malformed") from exc
    exact_mapping(evidence, {"schema_version", "subject", "owner_artifact", "public_site_acceptance", "common_checks", "documentation_semantics"}, "evidence")
    if evidence["schema_version"] != "website-pack-release-evidence/v1" or evidence["documentation_semantics"] is not None:
        raise ValueError("evidence schema mismatch")
    subject = exact_mapping(evidence["subject"], {"role", "manifest_identity", "source_coordinate", "version", "git_ref", "release_commit", "content_hash"}, "subject")
    version = tag.removeprefix("v")
    if subject != {"role": "design-system", "manifest_identity": "backstop-ai/backstop-design-system",
                   "source_coordinate": "backstop-ai/backstop-design-system", "version": version,
                   "git_ref": tag, "release_commit": tag_commit, "content_hash": subject.get("content_hash")}:
        raise ValueError("evidence tag/candidate identity mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(subject["content_hash"])):
        raise ValueError("evidence content hash is malformed")
    owner = exact_mapping(evidence["owner_artifact"], {"repository", "commit", "path", "sha256"}, "owner")
    if owner["repository"] != REPOSITORY or owner["commit"] != tag_commit or owner["path"] != "bundles/BUNDLE-001-design-system-release.bundle.md":
        raise ValueError("evidence owner binding mismatch")
    if owner["sha256"] != digest(blob(repo, tag_commit, owner["path"])):
        raise ValueError("evidence owner hash mismatch")
    acceptance = exact_mapping(evidence["public_site_acceptance"], {"schema_version", "subject_commit", "subject_content_hash", "export", "token_asset"}, "acceptance")
    if acceptance["schema_version"] != "backstop-design-system/public-site-acceptance/v1" or acceptance["subject_commit"] != tag_commit or acceptance["subject_content_hash"] != subject["content_hash"]:
        raise ValueError("evidence acceptance identity mismatch")
    export = exact_mapping(acceptance["export"], {"path", "sha256"}, "acceptance export")
    token = exact_mapping(acceptance["token_asset"], {"path", "media_type", "sha256"}, "token asset")
    if export["path"] != "contracts/public-site-acceptance.yml" or export["sha256"] != digest(blob(repo, tag_commit, export["path"])):
        raise ValueError("evidence acceptance hash mismatch")
    if token["path"] != "assets/design-system-tokens.css" or token["media_type"] != "text/css" or token["sha256"] != digest(blob(repo, tag_commit, token["path"])):
        raise ValueError("evidence token hash mismatch")
    checks = evidence["common_checks"]
    if not isinstance(checks, list) or [item.get("check") for item in checks if isinstance(item, dict)] != list(CHECKS):
        raise ValueError("evidence checks are missing, extra, or reordered")
    for item in checks:
        exact_mapping(item, {"check", "command", "exit_code", "result", "subject_commit", "subject_content_hash", "log_ref"}, "check")
        command, path = CHECKS[item["check"]]
        if item["command"] != command or item["exit_code"] != 0 or item["result"] != "pass" or item["subject_commit"] != tag_commit or item["subject_content_hash"] != subject["content_hash"]:
            raise ValueError(f"evidence check binding mismatch: {item['check']}")
        ref = exact_mapping(item["log_ref"], {"repository", "commit", "path", "sha256"}, "log ref")
        if ref["repository"] != REPOSITORY or ref["commit"] != log_commit or ref["commit"] == commit or ref["path"] != path:
            raise ValueError(f"evidence log-ref binding mismatch: {item['check']}")
        if ref["sha256"] != digest(blob(repo, log_commit, path)):
            raise ValueError(f"evidence log hash mismatch: {item['check']}")
    return True


def classify(args: argparse.Namespace) -> str:
    repo = Path(args.repo).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha):
        raise ValueError("candidate SHA must be a full lowercase commit SHA")
    if git(repo, "cat-file", "-t", args.candidate_sha) != "commit":
        raise ValueError("candidate SHA does not identify a commit")
    automatic = args.event_name == "workflow_run"
    if automatic:
        if args.workflow_run_head_sha != args.candidate_sha or args.workflow_run_head_branch != "main" or args.workflow_run_conclusion != "success":
            raise ValueError("workflow_run metadata does not bind the successful main candidate")
    elif args.event_name != "workflow_dispatch":
        raise ValueError("unsupported publication event")
    tag_ref = f"refs/tags/{args.tag}"
    if not git(repo, "rev-parse", "--verify", "--quiet", tag_ref, check=False):
        return "new-candidate"
    tag_commit = git(repo, "rev-parse", f"{tag_ref}^{{commit}}")
    if tag_commit == args.candidate_sha:
        return "resume-same-candidate"
    if not automatic or args.actor != BOT_NAME:
        raise ValueError("existing tag points at a different candidate")
    if subprocess.run(["git", "merge-base", "--is-ancestor", tag_commit, args.candidate_sha], cwd=repo).returncode:
        raise ValueError("post-tag candidate is not a descendant of the tag")
    try:
        if is_log_commit(repo, args.candidate_sha, tag_commit, args.tag) or is_evidence_commit(repo, args.candidate_sha, tag_commit, args.tag):
            return "post-tag-noop"
    except ValueError:
        raise
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
