#!/usr/bin/env python3
"""Named candidate checks for the v0.1.3 canonical-wordmark correction."""
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
OWNER = b'<a data-backstop-wordmark href="/"><span>./b</span><span>backstop</span><span>.sh</span></a>'
NEGATIVES = [
    "index-truncated-wordmark.html",
    "index-wrong-wordmark.html",
    "index-reordered-wordmark.html",
    "index-duplicate-wordmark-owner.html",
    "index-hidden-wordmark-compensation.html",
    "index-css-generated-wordmark.html",
]
ALLOWED_CANDIDATE_PATHS = {
    ".github/workflows/ci.yml", ".github/workflows/release.yml", "README.md",
    "bundles/BUNDLE-001-design-system-release.bundle.md", "contracts/public-site-acceptance.yml",
    "issues/ISSUE-001-canonical-wordmark-owner-v013.issue.md", "pack.yml",
    "plans/PLAN-ISSUE-001-canonical-wordmark-owner-v013.plan.yml",
    "recipes/jekyll-landing-page/payload/index.html", "recipes/jekyll-landing-page/recipe.yml",
    "release-evidence/template.yml", "rules/design-system.yml", "specs/.gitkeep",
    "scripts/classify-release-publication.py", "scripts/verify-canonical-wordmark-v013.py",
    "scripts/verify-public-site-acceptance.py", "scripts/verify-release-v013.py",
    "scripts/verify-release-workflow-safety.py",
    "fixtures/rules/valid/index.html",
    "fixtures/rules/invalid/index-inline-style.html", "fixtures/rules/invalid/index-inaccessible-shell.html",
    "fixtures/rules/invalid/index-duplicate-hero.html", "fixtures/rules/invalid/index-wrong-wordmark.html",
    "fixtures/rules/invalid/index-truncated-wordmark.html", "fixtures/rules/invalid/index-reordered-wordmark.html",
    "fixtures/rules/invalid/index-duplicate-wordmark-owner.html",
    "fixtures/rules/invalid/index-hidden-wordmark-compensation.html",
    "fixtures/rules/invalid/index-css-generated-wordmark.html",
}


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def findings(path: Path) -> list[str]:
    result = run([
        "semgrep", "--sarif", "--quiet", "--scan-unknown-extensions",
        "--disable-version-check", "--metrics=off", "--config",
        str(ROOT / "rules/design-system.yml"), str(path),
    ])
    if result.returncode not in (0, 1):
        raise AssertionError(f"semgrep dispatch failed for {path.name}: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    return [item.get("ruleId", "") for run_data in payload.get("runs", []) for item in run_data.get("results", [])]


def has_wordmark(path: Path) -> bool:
    return any(rule_id.endswith("canonical-wordmark") for rule_id in findings(path))


def test_owner() -> None:
    clean = ROOT / "fixtures/rules/valid/index.html"
    assert clean.read_bytes().count(OWNER) == 1, "clean fixture must contain one exact complete owner"
    assert not has_wordmark(clean), "complete owner must be accepted by the dispatched rule"


def test_truncated() -> None:
    assert has_wordmark(ROOT / "fixtures/rules/invalid/index-truncated-wordmark.html"), "truncated owner was accepted"


def test_matrix() -> None:
    for name in NEGATIVES:
        assert has_wordmark(ROOT / "fixtures/rules/invalid" / name), f"{name} was accepted"


def test_fixtures() -> None:
    result = run(["backstop", "pack", "test", "."])
    assert result.returncode == 0, result.stdout + result.stderr


def test_recipe() -> None:
    recipe = (ROOT / "recipes/jekyll-landing-page/payload/index.html").read_text(encoding="utf-8")
    assert recipe.count("data-backstop-wordmark") == 1, "recipe must emit exactly one marked owner"
    assert "./b</span><span>backstop</span><span" in recipe, "recipe owner is not the three-part contract"


def wordmark_cell() -> dict:
    contract = yaml.safe_load((ROOT / "contracts/public-site-acceptance.yml").read_text(encoding="utf-8"))
    return next(cell for cell in contract["cells"] if cell["id"] == "wordmark")


def test_acceptance_exact() -> None:
    cell = wordmark_cell()
    before = base64.b64decode(cell["mutation"]["unique_before_base64"], validate=True)
    replacement = base64.b64decode(cell["mutation"]["replacement_base64"], validate=True)
    clean = ROOT / cell["clean_fixture"]
    negative = ROOT / cell["negative_fixture"]
    assert b"<span>backstop</span>" in before, "wordmark mutation omits the semantic middle part"
    assert clean.read_bytes().count(before) == 1, "wordmark mutation source is not exact-once"
    assert clean.read_bytes().replace(before, replacement, 1) == negative.read_bytes(), "mutation does not equal targeted negative"


def test_acceptance_dispatch() -> None:
    cell = wordmark_cell()
    before = base64.b64decode(cell["mutation"]["unique_before_base64"], validate=True)
    replacement = base64.b64decode(cell["mutation"]["replacement_base64"], validate=True)
    source = (ROOT / cell["clean_fixture"]).read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        rendered = Path(directory) / cell["mutation"]["target_relative_path"]
        rendered.parent.mkdir(parents=True, exist_ok=True)
        rendered.write_bytes(source.replace(before, replacement, 1))
        assert has_wordmark(rendered), "exported mutation did not dispatch to canonical-wordmark"


def assert_spec_root(paths: set[str], read_bytes) -> None:
    spec_paths = {path for path in paths if path == "specs" or path.startswith("specs/")}
    assert spec_paths == {"specs/.gitkeep"}, f"only specs/.gitkeep is permitted, got {sorted(spec_paths)}"
    assert read_bytes("specs/.gitkeep") == b"", "specs/.gitkeep must be byte-empty"


def test_change_fence(base: str) -> None:
    evidence = f"release-evidence/{base}.yml"
    baseline = run(["git", "log", "-1", "--format=%H", "--", evidence])
    assert baseline.returncode == 0 and baseline.stdout.strip(), f"cannot locate baseline evidence commit for {base}"
    result = run(["git", "diff", "--name-only", f"{baseline.stdout.strip()}...HEAD"])
    assert result.returncode == 0, result.stderr
    changed = {line for line in result.stdout.splitlines() if line}
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    assert untracked.returncode == 0, untracked.stderr
    changed.update(untracked.stdout.splitlines())
    assert changed <= ALLOWED_CANDIDATE_PATHS, f"unrelated or Core paths changed: {sorted(changed - ALLOWED_CANDIDATE_PATHS)}"
    assert_spec_root(changed, lambda path: (ROOT / path).read_bytes())
    # Synthetic adversarial cases prove the root exception cannot admit a spec.
    assert_spec_root({"specs/.gitkeep"}, lambda _path: b"")
    for paths, payload in [
        ({"specs/.gitkeep", "specs/SPEC-001-feature.spec.md"}, b""),
        ({"specs/.gitkeep", "specs/nested/content.md"}, b""),
        ({"specs/.gitkeep"}, b"---\nspec_id: SPEC-001\n---\n"),
        ({"specs/.gitkeep"}, b"placeholder\n"),
    ]:
        try:
            assert_spec_root(paths, lambda _path, value=payload: value)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"synthetic forbidden specs case was accepted: {sorted(paths)}")
    pack = yaml.safe_load((ROOT / "pack.yml").read_text(encoding="utf-8"))
    assert pack["language"] == "any", "pack must remain language-neutral"
    assert pack["version"] == "0.1.3" and pack["content"]["ruleset"]["version"] == "1.3.0", "candidate identities are stale"


TESTS = {
    "TestCanonicalWordmark_AcceptsCompleteThreePartOwnerExactlyOnce": test_owner,
    "TestCanonicalWordmark_RejectsTruncatedOwner": test_truncated,
    "TestCanonicalWordmark_RejectsSemanticDriftMatrix": test_matrix,
    "TestPackFixtures_AllClaimsRetainSubstantivePolarity": test_fixtures,
    "TestCanonicalWordmark_RecipeSurfaceMatchesOwnerContract": test_recipe,
    "TestPublicSiteAcceptance_WordmarkMutationIsUniqueAndExact": test_acceptance_exact,
    "TestPublicSiteAcceptance_WordmarkMutationDispatchRejects": test_acceptance_dispatch,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="store_true", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--focus")
    args = parser.parse_args()
    selected = list(TESTS)
    if args.focus:
        selected = selected[:5]
    failures = 0
    for name in selected:
        try:
            TESTS[name]()
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError, StopIteration) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    name = "TestCanonicalWordmarkV013_ChangeFence"
    if not args.focus:
        try:
            test_change_fence(args.base)
            print(f"PASS {name}")
        except (AssertionError, KeyError, ValueError) as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
