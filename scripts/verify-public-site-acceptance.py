#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/public-site-acceptance.yml"
EXPECTED_CELLS = [
    ("token", "no-raw-colors"),
    ("inline-style", "no-inline-styles"),
    ("focus", "focus-visible-required"),
    ("reduced-motion", "reduced-motion-required"),
    ("accessibility", "accessible-site-shell"),
    ("wordmark", "canonical-wordmark"),
    ("reusable-presentation", "reusable-page-hero"),
]


def fail(message: str) -> None:
    raise SystemExit(f"public-site-acceptance: {message}")


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decoded(cell_id: str, field: str, value: object) -> bytes:
    if not isinstance(value, str):
        fail(f"cell {cell_id} {field} must be base64 text")
    try:
        result = base64.b64decode(value, validate=True)
    except ValueError as exc:
        fail(f"cell {cell_id} {field} is invalid base64: {exc}")
    if base64.b64encode(result).decode("ascii") != value:
        fail(f"cell {cell_id} {field} is not canonical base64")
    if not result:
        fail(f"cell {cell_id} {field} decodes to empty bytes")
    return result


def verify_wordmark_acceptance(cell: dict, clean: bytes, before: bytes, replacement: bytes) -> None:
    owner_start = clean.find(b"<a data-backstop-wordmark")
    owner_end = clean.find(b"</a>", owner_start)
    if owner_start < 0 or owner_end < 0 or not (owner_start < clean.find(before) < owner_end):
        fail("wordmark mutation source is not inside the marked owner")
    mutated = clean.replace(before, replacement, 1)
    with tempfile.TemporaryDirectory() as directory:
        rendered = Path(directory) / cell["mutation"]["target_relative_path"]
        rendered.parent.mkdir(parents=True, exist_ok=True)
        rendered.write_bytes(mutated)
        result = subprocess.run(
            ["semgrep", "--sarif", "--quiet", "--scan-unknown-extensions",
             "--disable-version-check", "--metrics=off", "--config",
             str(ROOT / "rules/design-system.yml"), str(rendered)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        if result.returncode not in (0, 1):
            fail(f"wordmark rule dispatch failed: {result.stderr.strip()}")
        try:
            sarif = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            fail(f"wordmark dispatch did not return SARIF: {exc}")
        rule_ids = [finding.get("ruleId", "") for run in sarif.get("runs", []) for finding in run.get("results", [])]
        if not any(rule_id.endswith("canonical-wordmark") for rule_id in rule_ids):
            fail("wordmark mutation was not rejected by canonical-wordmark")


contract = load_yaml(CONTRACT)
pack = load_yaml(ROOT / "pack.yml")

if contract.get("schema_version") != "backstop-design-system/public-site-acceptance/v1":
    fail("unexpected schema_version")
subject = contract.get("subject")
if not isinstance(subject, dict):
    fail("subject is required")
if subject.get("manifest_identity") != pack.get("name") or subject.get("version") != pack.get("version"):
    fail("subject identity/version does not match pack.yml")
ruleset = pack.get("content", {}).get("ruleset", {})
if subject.get("ruleset_version") != ruleset.get("version"):
    fail("subject ruleset_version does not match pack.yml")
if contract.get("export_fingerprint_binding") != "release-evidence/v0.1.3.yml#public_site_acceptance":
    fail("export fingerprint is not bound to the same release evidence")

declared_rules = {rule.get("id") for rule in ruleset.get("rules", []) if isinstance(rule, dict)}
cells = contract.get("cells")
if not isinstance(cells, list) or [(cell.get("id"), cell.get("rule_id")) for cell in cells] != EXPECTED_CELLS:
    fail("cells must be the exact ordered seven-cell matrix")

for cell in cells:
    cell_id = cell["id"]
    if cell["rule_id"] not in declared_rules:
        fail(f"cell {cell_id} references an undeclared rule")
    clean_path = ROOT / cell.get("clean_fixture", "")
    negative_path = ROOT / cell.get("negative_fixture", "")
    if not clean_path.is_file() or not negative_path.is_file():
        fail(f"cell {cell_id} fixture is missing")
    mutation = cell.get("mutation")
    fidelity = cell.get("path_fidelity")
    filters = cell.get("path_filters")
    if not all(isinstance(item, dict) for item in (mutation, fidelity, filters)):
        fail(f"cell {cell_id} mutation, fidelity, and path_filters are required")
    target = mutation.get("target_relative_path")
    if target not in filters.get("include", []) or target in filters.get("exclude", []):
        fail(f"cell {cell_id} target does not match its production filters")
    if fidelity.get("fixture_relative_path") != cell.get("negative_fixture") or fidelity.get("target_relative_path") != target:
        fail(f"cell {cell_id} path-fidelity tuple disagrees with its fixture/mutation")
    if fidelity.get("dispatch_evidence_ref") != "release-evidence/v0.1.3.yml#common_checks.pack-test":
        fail(f"cell {cell_id} dispatch evidence is not same-release")
    before = decoded(cell_id, "unique_before_base64", mutation.get("unique_before_base64"))
    replacement = decoded(cell_id, "replacement_base64", mutation.get("replacement_base64"))
    clean = clean_path.read_bytes()
    if clean.count(before) != 1:
        fail(f"cell {cell_id} before bytes must occur exactly once in its clean fixture")
    if clean.replace(before, replacement, 1) != negative_path.read_bytes():
        fail(f"cell {cell_id} negative fixture is not the exact exported mutation")
    if cell_id == "wordmark":
        verify_wordmark_acceptance(cell, clean, before, replacement)

token = contract.get("token_asset")
if not isinstance(token, dict):
    fail("token_asset is required")
token_path = ROOT / token.get("installed_relative_path", "")
if token.get("media_type") != "text/css" or token.get("public_output") != "assets/css/design-system-tokens.css":
    fail("token asset media type/output is invalid")
if not token_path.is_file() or digest(token_path) != token.get("sha256"):
    fail("token asset hash does not match installed bytes")

protected = contract.get("protected_file_fingerprints")
if not isinstance(protected, list):
    fail("protected_file_fingerprints is required")
protected_map = {entry.get("path"): entry.get("sha256") for entry in protected if isinstance(entry, dict)}
expected_paths = {"pack.yml", "rules/design-system.yml", token.get("installed_relative_path")}
expected_paths.update(str(path.relative_to(ROOT)) for path in (ROOT / "fixtures").rglob("*") if path.is_file())
if set(protected_map) != expected_paths or len(protected_map) != len(protected):
    fail("protected fingerprints do not cover the exact rule/engine/fixture/token set")
for relative, expected in protected_map.items():
    path = ROOT / relative
    if not path.is_file() or digest(path) != expected:
        fail(f"protected fingerprint mismatch: {relative}")

print("public-site-acceptance: PASS")
