#!/usr/bin/env python3
"""Substantive candidate dispatch checks for the v0.1.5 wordmark correction."""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULE_ID = "rules.canonical-wordmark"
OWNER = b'<a data-backstop-wordmark href="/"><span>./b</span><span>backstop</span><span>.sh</span></a>'
LEGACY_NEGATIVES = [
    "index-truncated-wordmark.html", "index-wrong-wordmark.html",
    "index-reordered-wordmark.html", "index-duplicate-wordmark-owner.html",
    "index-hidden-wordmark-compensation.html", "index-css-generated-wordmark.html",
]
CONCEALMENT_NEGATIVES = [
    ("owner:hidden", "index-hidden-wordmark-owner.html"),
    ("owner:aria-hidden", "index-aria-hidden-wordmark-owner.html"),
    ("owner:inline-display-none", "index-inline-concealed-wordmark-owner.html"),
    ("component:hidden", "index-hidden-wordmark-compensation.html"),
    ("component:aria-hidden", "index-aria-hidden-wordmark-component.html"),
    ("component:inline-display-none", "index-inline-concealed-wordmark-component.html"),
]


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def findings(path: Path) -> list[str]:
    result = run(["semgrep", "--sarif", "--quiet", "--scan-unknown-extensions",
                  "--disable-version-check", "--metrics=off", "--config",
                  str(ROOT / "rules/design-system.yml"), str(path)])
    assert result.returncode in (0, 1), f"semgrep dispatch failed for {path.name}: {result.stderr.strip()}"
    payload = json.loads(result.stdout)
    return [item.get("ruleId", "") for execution in payload.get("runs", [])
            for item in execution.get("results", [])]


def canonical_findings(path: Path) -> list[str]:
    return [rule_id for rule_id in findings(path) if rule_id == RULE_ID]


def test_exact_owner() -> None:
    fixture = ROOT / "fixtures/rules/valid/index.html"
    assert fixture.read_bytes().count(OWNER) == 1, "positive fixture must contain one full exact owner"
    assert canonical_findings(fixture) == [], "exact visible owner was rejected by canonical-wordmark"


def test_prefixed_owner() -> None:
    fixture = ROOT / "fixtures/rules/invalid/index-prefixed-wordmark-owner.html"
    assert fixture.read_bytes().count(b"data-backstop-wordmark-foo") == 1
    assert canonical_findings(fixture) == [RULE_ID], "prefixed marker was accepted by canonical-wordmark"


def test_concealment() -> None:
    accepted = []
    for label, name in CONCEALMENT_NEGATIVES:
        actual = canonical_findings(ROOT / "fixtures/rules/invalid" / name)
        if actual != [RULE_ID]:
            accepted.append(label)
    assert not accepted, f"concealment accepted by canonical-wordmark: {', '.join(accepted)}"


def test_truncated() -> None:
    assert canonical_findings(ROOT / "fixtures/rules/invalid/index-truncated-wordmark.html") == [RULE_ID]


def test_matrix() -> None:
    for name in LEGACY_NEGATIVES:
        assert canonical_findings(ROOT / "fixtures/rules/invalid" / name) == [RULE_ID], f"{name} was accepted"


def test_pack() -> None:
    result = run(["backstop", "pack", "test", "."])
    assert result.returncode == 0, result.stdout + result.stderr


def test_recipe() -> None:
    source = (ROOT / "recipes/jekyll-landing-page/payload/index.html").read_bytes()
    assert source.count(b"data-backstop-wordmark") == 1
    assert b"./b</span><span>backstop</span><span" in source, "recipe does not retain the full exact owner"


def wordmark_cell() -> dict:
    contract = yaml.safe_load((ROOT / "contracts/public-site-acceptance.yml").read_text())
    return next(cell for cell in contract["cells"] if cell["id"] == "wordmark")


def test_acceptance_exact() -> None:
    cell = wordmark_cell()
    before = base64.b64decode(cell["mutation"]["unique_before_base64"], validate=True)
    after = base64.b64decode(cell["mutation"]["replacement_base64"], validate=True)
    clean = (ROOT / cell["clean_fixture"]).read_bytes()
    assert clean.count(before) == 1
    assert clean.replace(before, after, 1) == (ROOT / cell["negative_fixture"]).read_bytes()


def test_acceptance_dispatch() -> None:
    cell = wordmark_cell()
    before = base64.b64decode(cell["mutation"]["unique_before_base64"], validate=True)
    after = base64.b64decode(cell["mutation"]["replacement_base64"], validate=True)
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "index.html"
        target.write_bytes((ROOT / cell["clean_fixture"]).read_bytes().replace(before, after, 1))
        assert canonical_findings(target) == [RULE_ID]


TESTS = {
    "TestCanonicalWordmark_AcceptsCompleteThreePartOwnerExactlyOnce": test_exact_owner,
    "TestCanonicalWordmark_RejectsTruncatedOwner": test_truncated,
    "TestCanonicalWordmark_RejectsSemanticDriftMatrix": test_matrix,
    "TestPackFixtures_AllClaimsRetainSubstantivePolarity": test_pack,
    "TestCanonicalWordmark_RecipeSurfaceMatchesOwnerContract": test_recipe,
    "TestPublicSiteAcceptance_WordmarkMutationIsUniqueAndExact": test_acceptance_exact,
    "TestPublicSiteAcceptance_WordmarkMutationDispatchRejects": test_acceptance_dispatch,
    "TestCanonicalWordmarkV015_AcceptsExactVisibleOwnerByDispatch": test_exact_owner,
    "TestCanonicalWordmarkV015_RejectsPrefixedOwnerMarkerByDispatch": test_prefixed_owner,
    "TestCanonicalWordmarkV015_RejectsOwnerAndComponentConcealmentByDispatch": test_concealment,
}


def test_change_fence(base: str) -> None:
    manifest = ROOT / "release-candidate-v015.paths"
    assert manifest.is_file(), "authoritative v0.1.5 candidate manifest is missing"
    expected = manifest.read_text().splitlines()
    assert expected == sorted(set(expected)) and len(expected) == 21, "candidate manifest must contain 21 sorted unique paths"
    baseline = run(["git", "log", "-1", "--format=%H", "--", f"release-evidence/{base}.yml"])
    assert baseline.returncode == 0 and baseline.stdout.strip()
    changed = set(run(["git", "diff", "--name-only", baseline.stdout.strip()]).stdout.splitlines())
    changed.update(run(["git", "ls-files", "--others", "--exclude-standard"]).stdout.splitlines())
    assert changed == set(expected), f"candidate fence mismatch: missing={sorted(set(expected)-changed)} extra={sorted(changed-set(expected))}"
    pack = yaml.safe_load((ROOT / "pack.yml").read_text())
    assert (pack["version"], pack["content"]["ruleset"]["version"]) == ("0.1.5", "1.3.1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="store_true", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    failures = 0
    for name, test in TESTS.items():
        try:
            test()
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError, StopIteration, json.JSONDecodeError) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    name = "TestCanonicalWordmarkV015_ReviewCorrectionChangeFence"
    try:
        test_change_fence(args.base)
        print(f"PASS {name}")
    except (AssertionError, KeyError, ValueError) as exc:
        failures += 1
        print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
