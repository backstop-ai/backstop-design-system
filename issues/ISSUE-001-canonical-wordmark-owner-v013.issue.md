---
title: "Release v0.1.3 With the Complete Canonical Wordmark Contract"
schema_version: issue/v1

issue:
  id: ISSUE-001
  title: "Release v0.1.3 With the Complete Canonical Wordmark Contract"
  type: bug
  status: ready
  created: "2026-08-28"

complexity:
  scope: contained
  uncertainty: known
  risk: moderate

verification:
  level: integration
  coverage_threshold: 80
  test_command: backstop pack check . && backstop pack test . && python3 scripts/verify-public-site-acceptance.py

implementation:
  summary: >
    Correct the design-system pack's owned canonical-wordmark rule, fixtures,
    applicable recipe output, public-site acceptance export and verifier, protected
    fingerprints, release identities, and immutable publication evidence so v0.1.3
    substantively requires the complete three-part ./b backstop.sh markup.
  package: backstop-ai/backstop-design-system

requirements:
  - id: REQ-001
    text: >
      The canonical-wordmark owner contract must require one marked canonical
      wordmark composed from three source-visible elements in order: `./b`,
      `backstop`, and `.sh`, rendering the complete `./b backstop.sh` identity.
      The middle `backstop` text must be semantic markup, not CSS-generated content,
      an accessible-only or visually hidden duplicate, or an unrelated occurrence
      elsewhere in the document. The existing truncated two-part `./b` plus `.sh`
      form must fail.
  - id: REQ-002
    text: >
      The canonical-wordmark rule and declared claim must reject loss, substitution,
      reordering, duplication, or concealment of any of the three canonical parts.
      Substantive positive and targeted negative fixtures must prove the complete
      form passes while the truncated form, a wrong part, a duplicate marked owner,
      a hidden compensating duplicate, and CSS-generated semantic text do not create
      false green results. Other design-system rules must retain their fixture
      polarity and behavior.
  - id: REQ-003
    text: >
      Every pack-owned recipe surface that emits or identifies the canonical
      wordmark must agree with the corrected contract. A generated page must not
      carry multiple `data-backstop-wordmark` owners merely to satisfy a file-level
      existence check, and any legitimate secondary visual mark must not become a
      hidden semantic substitute for the single contract carrier. Recipe metadata
      and versioning must change only where repository conventions require it.
  - id: REQ-004
    text: >
      The public-site acceptance wordmark cell must export a deterministic mutation
      from the complete canonical three-part owner markup to a genuinely invalid
      form. Its exact `unique_before` bytes must occur once at the marked mutation
      site, must include the `backstop` middle element, and must correspond to the
      clean and negative owner fixtures. The verifier must prove both the exact-once
      source/mutation relationship and that dispatching the mutated rendered-site
      contract through the released canonical-wordmark rule produces the expected
      rejection; byte replacement equality or a stored evidence pointer alone is
      not sufficient.
  - id: REQ-005
    text: >
      Publish the correction as pack release v0.1.3, updating the pack, ruleset,
      contract subject and same-release bindings, BUNDLE-001 release identity,
      protected file fingerprints, verifier expectations, release template, and
      immutable v0.1.3 evidence according to this repository's established release
      conventions. The release evidence must bind the released commit and content
      hash to passing pack-check, pack-test, and public-site-acceptance results from
      the released bytes.
  - id: REQ-006
    text: >
      Keep the change narrowly limited to the owner wordmark correction required by
      Core ISSUE-190 and its v0.1.3 release proof. The pack remains external,
      language-neutral (`language: any`), engine-driven, and free of Core-specific
      paths or baked language/tool behavior. No broad visual redesign, unrelated
      rule change, consumer-site implementation, or weakened/skipped/vacuous check
      is in scope.

claims:
  - id: CLM-001
    requirement: REQ-001
    text: The owner rule accepts exactly the complete source-visible three-part canonical mark and rejects the currently exported truncated form.
    tests:
      - TestCanonicalWordmark_AcceptsCompleteThreePartOwnerExactlyOnce
      - TestCanonicalWordmark_RejectsTruncatedOwner
  - id: CLM-002
    requirement: REQ-002
    text: Positive and negative fixture dispatch rejects missing, wrong, reordered, duplicated, hidden, and CSS-generated substitutes without disturbing other rule claims.
    tests:
      - TestCanonicalWordmark_RejectsSemanticDriftMatrix
      - TestPackFixtures_AllClaimsRetainSubstantivePolarity
  - id: CLM-003
    requirement: REQ-003
    text: Applicable recipe output has one canonical contract carrier whose source markup agrees with the owner rule and does not rely on a duplicate.
    tests:
      - TestCanonicalWordmark_RecipeSurfaceMatchesOwnerContract
  - id: CLM-004
    requirement: REQ-004
    text: The acceptance export identifies the complete canonical mutation source exactly once and the exported mutation is demonstrated to fail the canonical-wordmark contract.
    tests:
      - TestPublicSiteAcceptance_WordmarkMutationIsUniqueAndExact
      - TestPublicSiteAcceptance_WordmarkMutationDispatchRejects
  - id: CLM-005
    requirement: REQ-005
    text: v0.1.3 carries synchronized pack, ruleset, contract, fingerprint, verifier, owner-artifact, and immutable release-evidence identities with all release checks passing.
    tests:
      - TestReleaseV013_WordmarkIdentityAndEvidenceAreBound
  - id: CLM-006
    requirement: REQ-006
    text: The delivered diff is confined to the external language-neutral design-system owner's wordmark and release surfaces.
    tests:
      - TestCanonicalWordmarkV013_ChangeFence

contracts:
  - file: rules/design-system.yml
    provides:
      - name: canonical_wordmark
        kind: variable
        signature: "one data-backstop-wordmark owner with ordered source-visible ./b, backstop, and .sh elements"
  - file: contracts/public-site-acceptance.yml
    provides:
      - name: wordmark_acceptance_cell
        kind: variable
        signature: "v0.1.3 exact-once complete-mark mutation with same-release path-fidelity evidence"
  - file: scripts/verify-public-site-acceptance.py
    provides:
      - name: verify_wordmark_acceptance
        kind: function
        signature: "verify exact complete owner source once and prove its exported mutation is rejected"
  - file: pack.yml
    provides:
      - name: release_identity
        kind: constant
        signature: "backstop-ai/backstop-design-system v0.1.3 with convention-compliant ruleset version"
---

# Release v0.1.3 With the Complete Canonical Wordmark Contract

## Problem

Core ISSUE-190 must restore the approved homepage's complete `./b backstop.sh`
wordmark using the canonical three-part markup. The external design-system pack is
the owner of that visual contract, but released v0.1.2 describes and tests only two
parts. `fixtures/rules/valid/index.html` treats
`<span>./b</span><span>.sh</span>` as valid; `rules/design-system.yml` checks only
for an occurrence of `./b` and `.sh`; and the public-site acceptance wordmark cell
exports that same truncated two-span sequence as its exact mutation source. A Core
page that correctly restores the `backstop` middle element therefore cannot match
the owner export, while a page that loses the middle of the brand remains green.

The current rule is also file-level and existential. Unrelated text or duplicate
and hidden markup can satisfy its lookaheads, and the acceptance verifier proves
only that encoded bytes occur once in the owner clean fixture and reproduce the
stored negative fixture. It does not itself demonstrate that the exported mutation
is rejected when dispatched through the owner rule. This leaves a vacuous path in
the cross-repository acceptance contract precisely where Core needs a trustworthy
mutation for ISSUE-190.

The pack's own landing-page recipe already contains the intended three visible
parts, but it marks more than one wordmark owner in one page. Rule fixtures, recipe
surface, acceptance export, fingerprints, verifier constants, version identities,
and release evidence consequently do not agree on one enforceable canonical
contract.

## Solution

Release the focused owner correction as v0.1.3. Make the complete ordered
three-part source markup authoritative at a single marked contract carrier; harden
the rule and fixtures against truncation, substitution, reordering, duplication,
hidden compensation, and generated-content compensation; reconcile any recipe
surface that declares the owner; and export a unique mutation that removes or
corrupts a substantive part of that complete mark. Extend owner verification so it
executes enough of the real rule path to prove the mutation is rejected rather than
merely checking fixture bytes.

Carry the resulting changes through the repository's established pack/ruleset
version, protected-fingerprint, bundle release identity, same-release evidence, and
tagged-publication conventions. Do not implement the Core homepage here and do not
broaden this into a redesign of the pack's other six public-site cells.

## Verification

Run the real owner checks from the release candidate bytes:

1. `backstop pack check .`
2. `backstop pack test .`
3. `python3 scripts/verify-public-site-acceptance.py`

Coverage must include the complete positive owner and a targeted negative matrix
for truncation, wrong/reordered parts, duplicate marked owners, hidden compensation,
and generated-content compensation. The public-site verifier must confirm the
complete mutation source occurs exactly once at the owner site, reproduces its
negative fixture, and genuinely causes canonical-wordmark rejection. Publication
evidence for v0.1.3 must record passing results from the immutable released bytes.

## References

- Core `ISSUE-190`, especially REQ-001 and its complete `./b backstop.sh`
  acceptance target.
- `pack.yml` canonical-wordmark declaration and v0.1.2 / ruleset v1.2.0 identity.
- `rules/design-system.yml` canonical-wordmark lookaheads.
- `fixtures/rules/valid/index.html` and
  `fixtures/rules/invalid/index-wrong-wordmark.html`.
- `recipes/jekyll-landing-page/payload/index.html`.
- `contracts/public-site-acceptance.yml` wordmark cell and protected fingerprints.
- `scripts/verify-public-site-acceptance.py`.
- `release-evidence/v0.1.2.yml`, `release-evidence/template.yml`, and the release
  workflow's released-byte checks.
- BUNDLE-001 owns the general design-system release line and currently records
  v0.1.2. This issue is the reactive correction for the concrete released wordmark
  defect needed by Core, not a competing proactive design-system charter.

### Existence-in-world check

Before filing, this repository's `issues/` and `bundles/` were searched. No prior
issue existed. BUNDLE-001 records the already-published general release line at
v0.1.2 but does not identify or resolve this released wordmark defect; this issue
is the focused reactive owner for its v0.1.3 correction.
