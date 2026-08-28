#!/usr/bin/env python3
"""Independent v0.1.5 proof. Its output is never release evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
V013 = "cb35c69e89844c5955d51b1b10e67da938010039"
V014 = "71face4c4738b6652fb308348ab5676f2a056ff2"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
REPOSITORY = "https://github.com/backstop-ai/backstop-design-system.git"
NAMES = [
    "TestReleaseV015_AuthenticatesEvidenceSchemaCommitAndPath",
    "TestReleaseV015_AuthenticatesContentOwnerAcceptanceTokenAndLogs",
    "TestReleaseV015_DispatchesTaggedCanonicalRuleAndFixtures",
    "TestReleaseV015_ProofIsIndependentAndNonCircular",
    "TestReleaseV015_VersionEvidenceAndHashesAreSynchronized",
    "TestReleaseV015_PreservesCanonicalFullWordmark",
    "TestReleaseV015_PreservesV013AndV014TagIdentity",
    "TestReleaseV015_ReviewCorrectionChangeFence",
]
CHECKS = {
    "pack-check": ("backstop pack check .", "release-evidence/logs/pack-check.log"),
    "pack-test": ("backstop pack test .", "release-evidence/logs/pack-test.log"),
    "public-site-acceptance": ("python3 scripts/verify-public-site-acceptance.py", "release-evidence/logs/public-site-acceptance.log"),
    "canonical-wordmark-v015-candidate": ("python3 scripts/verify-canonical-wordmark-v015.py --candidate --base v0.1.4", "release-evidence/logs/canonical-wordmark-v015-candidate.log"),
    "release-workflow-safety": ("python3 scripts/verify-release-workflow-safety.py", "release-evidence/logs/release-workflow-safety.log"),
}
NEGATIVES = [
    "index-truncated-wordmark.html", "index-wrong-wordmark.html", "index-reordered-wordmark.html",
    "index-duplicate-wordmark-owner.html", "index-hidden-wordmark-compensation.html",
    "index-css-generated-wordmark.html", "index-prefixed-wordmark-owner.html",
    "index-hidden-wordmark-owner.html", "index-aria-hidden-wordmark-owner.html",
    "index-inline-concealed-wordmark-owner.html", "index-aria-hidden-wordmark-component.html",
    "index-inline-concealed-wordmark-component.html",
]


def git(repo: Path, *args: str, text: bool = True):
    result = subprocess.run(["git", *args], cwd=repo, text=text, capture_output=True, check=False)
    if result.returncode:
        error = result.stderr.strip() if text else result.stderr.decode().strip()
        raise AssertionError(error)
    return result.stdout.strip() if text else result.stdout


def blob(repo: Path, commit: str, path: str) -> bytes:
    return git(repo, "show", f"{commit}:{path}", text=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(repo: Path, commit: str) -> str:
    paths = git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
    manifest = "\n".join(f"{path}:{digest(blob(repo, commit, path))}" for path in sorted(paths))
    return digest(manifest.encode())


def exact(value: object, keys: set[str], label: str) -> dict:
    assert isinstance(value, dict) and set(value) == keys, f"{label} fields mismatch"
    return value


def identity(repo: Path, commit: str, message: str) -> None:
    fields = git(repo, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%s", commit).split("\0")
    assert fields == [BOT_NAME, BOT_EMAIL, BOT_NAME, BOT_EMAIL, message], "automation identity/message mismatch"


def load_graph(tag: str, candidate: str, evidence_commit: str) -> tuple[dict, str]:
    assert re.fullmatch(r"[0-9a-f]{40}", candidate) and re.fullmatch(r"[0-9a-f]{40}", evidence_commit)
    assert git(ROOT, "rev-parse", f"{tag}^{{commit}}") == candidate, "tag does not bind exact candidate"
    evidence_parents = git(ROOT, "rev-list", "--parents", "-n", "1", evidence_commit).split()[1:]
    assert len(evidence_parents) == 1
    log_commit = evidence_parents[0]
    assert git(ROOT, "rev-list", "--parents", "-n", "1", log_commit).split()[1:] == [candidate]
    identity(ROOT, log_commit, "Record v0.1.5 publication checks")
    identity(ROOT, evidence_commit, "Publish v0.1.5 release evidence")
    assert set(git(ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", evidence_commit).splitlines()) == {"release-evidence/v0.1.5.yml"}
    changed_logs = set(git(ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", log_commit).splitlines())
    assert changed_logs and changed_logs <= {path for _, path in CHECKS.values()}
    evidence = yaml.safe_load(blob(ROOT, evidence_commit, "release-evidence/v0.1.5.yml"))
    return evidence, log_commit


def validate_evidence(evidence: object, candidate: str, log_commit: str) -> None:
    document = exact(evidence, {"schema_version", "subject", "owner_artifact", "public_site_acceptance", "common_checks", "documentation_semantics"}, "evidence")
    assert document["schema_version"] == "website-pack-release-evidence/v1" and document["documentation_semantics"] is None
    subject = exact(document["subject"], {"role", "manifest_identity", "source_coordinate", "version", "git_ref", "release_commit", "content_hash"}, "subject")
    derived = content_hash(ROOT, candidate)
    assert subject == {"role": "design-system", "manifest_identity": "backstop-ai/backstop-design-system",
                       "source_coordinate": "backstop-ai/backstop-design-system", "version": "0.1.5",
                       "git_ref": "v0.1.5", "release_commit": candidate, "content_hash": derived}
    owner = exact(document["owner_artifact"], {"repository", "commit", "path", "sha256"}, "owner")
    assert owner == {"repository": REPOSITORY, "commit": candidate,
                     "path": "bundles/BUNDLE-001-design-system-release.bundle.md",
                     "sha256": digest(blob(ROOT, candidate, "bundles/BUNDLE-001-design-system-release.bundle.md"))}
    acceptance = exact(document["public_site_acceptance"], {"schema_version", "subject_commit", "subject_content_hash", "export", "token_asset"}, "acceptance")
    assert acceptance["schema_version"] == "backstop-design-system/public-site-acceptance/v1"
    assert acceptance["subject_commit"] == candidate and acceptance["subject_content_hash"] == derived
    export = exact(acceptance["export"], {"path", "sha256"}, "export")
    token = exact(acceptance["token_asset"], {"path", "media_type", "sha256"}, "token")
    assert export == {"path": "contracts/public-site-acceptance.yml", "sha256": digest(blob(ROOT, candidate, "contracts/public-site-acceptance.yml"))}
    assert token == {"path": "assets/design-system-tokens.css", "media_type": "text/css",
                     "sha256": digest(blob(ROOT, candidate, "assets/design-system-tokens.css"))}
    checks = document["common_checks"]
    assert isinstance(checks, list) and [item.get("check") for item in checks if isinstance(item, dict)] == list(CHECKS)
    for item in checks:
        exact(item, {"check", "command", "exit_code", "result", "subject_commit", "subject_content_hash", "log_ref"}, "check")
        command, path = CHECKS[item["check"]]
        assert item["command"] == command and type(item["exit_code"]) is int and item["exit_code"] == 0
        assert item["result"] == "pass" and item["subject_commit"] == candidate and item["subject_content_hash"] == derived
        ref = exact(item["log_ref"], {"repository", "commit", "path", "sha256"}, "log")
        assert ref == {"repository": REPOSITORY, "commit": log_commit, "path": path,
                       "sha256": digest(blob(ROOT, log_commit, path))}


def fresh_commands(candidate: str, evidence: dict, log_commit: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory) / "candidate"
        clone = subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(checkout)], capture_output=True, text=True)
        assert clone.returncode == 0, clone.stderr
        git(checkout, "checkout", "--quiet", "--detach", candidate)
        for item in evidence["common_checks"]:
            result = subprocess.run(item["command"], cwd=checkout, shell=True, capture_output=True, check=False)
            assert result.returncode == 0, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace")
            assert result.stdout == blob(ROOT, log_commit, item["log_ref"]["path"]), f"fresh output mismatch: {item['check']}"


def dispatch_tagged(candidate: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory) / "candidate"
        subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(checkout)], check=True)
        git(checkout, "checkout", "--quiet", "--detach", candidate)
        def ids(path: Path) -> list[str]:
            result = subprocess.run(["semgrep", "--sarif", "--quiet", "--scan-unknown-extensions",
                "--disable-version-check", "--metrics=off", "--config", str(checkout/"rules/design-system.yml"), str(path)],
                cwd=checkout, text=True, capture_output=True, check=False)
            assert result.returncode in (0, 1), result.stderr
            payload = json.loads(result.stdout)
            return [finding.get("ruleId", "") for run in payload.get("runs", []) for finding in run.get("results", [])]
        positive = checkout / "fixtures/rules/valid/index.html"
        assert "rules.canonical-wordmark" not in ids(positive)
        for name in NEGATIVES:
            assert "rules.canonical-wordmark" in ids(checkout / "fixtures/rules/invalid" / name), name


def synchronize_self_test() -> None:
    manifest = (ROOT / "release-candidate-v015.paths").read_text().splitlines()
    assert manifest == sorted(set(manifest)) and len(manifest) == 21
    pack = yaml.safe_load((ROOT / "pack.yml").read_text())
    assert (pack["version"], pack["content"]["ruleset"]["version"]) == ("0.1.5", "1.3.1")
    template = yaml.safe_load((ROOT / "release-evidence/template.yml").read_text())
    assert [(item["check"], item["command"], item["log_ref"]["path"]) for item in template["common_checks"]] == [
        (name, command, path) for name, (command, path) in CHECKS.items()]
    surfaces = "\n".join((ROOT / path).read_text() for path in [
        ".github/workflows/ci.yml", ".github/workflows/release.yml", "scripts/classify-release-publication.py",
        "scripts/verify-release-workflow-safety.py", "scripts/verify-public-site-acceptance.py"])
    assert "canonical-wordmark-v015-candidate" in surfaces and "--base v0.1.4" in surfaces
    release = (ROOT / ".github/workflows/release.yml").read_text()
    exact_command = 'python3 scripts/verify-release-v015.py --tag "$TAG" --candidate-sha "$CANDIDATE_SHA" --evidence-commit "$EVIDENCE_COMMIT"'
    assert exact_command in release
    # Independent shape adversaries: extra, missing, and retyped keys fail exact().
    for value in [{"a": 1, "extra": 2}, {}, {"a": "1"}]:
        try:
            mapped = exact(value, {"a"}, "self-test")
            assert type(mapped["a"]) is int
        except AssertionError:
            continue
        raise AssertionError("adversarial exact-shape mutation was accepted")
    assert git(ROOT, "rev-parse", "v0.1.3^{commit}") == V013
    assert git(ROOT, "rev-parse", "v0.1.4^{commit}") == V014


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v0.1.5")
    parser.add_argument("--candidate-sha", default="")
    parser.add_argument("--evidence-commit", default="")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        synchronize_self_test()
        print("release-v015-self-test: PASS")
        return 0
    failures: dict[str, str] = {}
    evidence = None; log_commit = ""
    tests = []
    def schema_test():
        nonlocal evidence, log_commit
        evidence, log_commit = load_graph(args.tag, args.candidate_sha, args.evidence_commit)
        validate_evidence(evidence, args.candidate_sha, log_commit)
    tests.append(schema_test)
    tests.append(lambda: validate_evidence(evidence, args.candidate_sha, log_commit))
    tests.append(lambda: dispatch_tagged(args.candidate_sha))
    tests.append(lambda: fresh_commands(args.candidate_sha, evidence, log_commit))
    tests.append(synchronize_self_test)
    tests.append(lambda: (assert_full_wordmark(args.candidate_sha)))
    tests.append(assert_prior_tags)
    tests.append(lambda: assert_fence(args.candidate_sha, args.evidence_commit))
    for name, test in zip(NAMES, tests):
        try: test()
        except (AssertionError, KeyError, TypeError, ValueError, yaml.YAMLError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
            failures[name] = str(exc)
    for name in NAMES:
        print(f"FAIL {name}: {failures[name]}" if name in failures else f"PASS {name}")
    return 1 if failures else 0


def assert_full_wordmark(candidate: str) -> None:
    owner = b'<a data-backstop-wordmark href="/"><span>./b</span><span>backstop</span><span>.sh</span></a>'
    assert blob(ROOT, candidate, "fixtures/rules/valid/index.html").count(owner) == 1
    pack = yaml.safe_load(blob(ROOT, candidate, "pack.yml"))
    assert len(pack["content"]["ruleset"]["rules"]) == 7


def assert_prior_tags() -> None:
    for tag, expected in [("v0.1.3", V013), ("v0.1.4", V014)]:
        assert git(ROOT, "rev-parse", f"{tag}^{{commit}}") == expected
        assert git(ROOT, "ls-remote", "--tags", "origin", f"refs/tags/{tag}").split()[0] == expected


def assert_fence(candidate: str, evidence_commit: str) -> None:
    assert git(ROOT, "merge-base", "--is-ancestor", candidate, evidence_commit) == ""
    assert subprocess.run(["git", "merge-base", "--is-ancestor", evidence_commit, candidate], cwd=ROOT).returncode != 0
    assert set((ROOT / "release-candidate-v015.paths").read_text().splitlines()) == set(git(ROOT, "diff", "--name-only", "1f56706", candidate).splitlines())


if __name__ == "__main__":
    sys.exit(main())
