---
title: "Correct v0.1.4 Independent Review Findings in v0.1.5"
schema_version: issue/v1

issue:
  id: ISSUE-003
  title: "Correct v0.1.4 Independent Review Findings in v0.1.5"
  type: bug
  status: ready
  created: "2026-08-28"

complexity:
  scope: contained
  uncertainty: known
  risk: critical

verification:
  level: integration
  coverage_threshold: 80
  test_command: backstop pack check . && backstop pack test . && python3 scripts/verify-public-site-acceptance.py && python3 scripts/verify-release-workflow-safety.py

implementation:
  summary: >
    Correct the four independent implementation-review failures in the published
    v0.1.4 wordmark rule, publication classifier, adversarial safety verifier, and
    independent release proof, then publish the synchronized correction as v0.1.5
    without changing immutable prior releases or Core.
  package: backstop-ai/backstop-design-system

requirements:
  - id: REQ-001
    text: >
      The canonical-wordmark rule must recognize only the exact
      `data-backstop-wordmark` owner attribute, not an attribute whose name merely
      starts with that token such as `data-backstop-wordmark-foo`. The sole owner
      and each of its three component spans must remain source-visible: `hidden`,
      `aria-hidden=true`, inline concealment, or an equivalent owner/component
      concealment must be rejected. Substantive dispatch fixtures must prove one
      exact, visible `./b`, `backstop`, `.sh` owner passes and separately prove the
      prefix-owner and owner/component concealment variants fail through the real
      released rule path.
  - id: REQ-002
    text: >
      Publication classification must independently derive or authenticate the
      subject content hash from the immutable candidate/package bytes using the
      repository's actual package-content identity contract. It must not accept an
      arbitrary well-formed 64-hex value merely because that value is repeated
      consistently in subject, acceptance, and check fields. Classification must
      fail closed for forged, stale, malformed, or missing content hashes and for
      missing, stale, forged, reordered, or cross-commit log/evidence bindings,
      while preserving authentic byte-identical post-tag publication descendants.
  - id: REQ-003
    text: >
      The release-workflow safety verifier's mandated adversarial cases must be
      distinct substantive implementations rather than aliases that invoke the
      same helper scenario or incomplete shape checks. Executable positive and
      negative histories must independently cover content-hash derivation and
      forgery; required log bytes and hashes; check commands, results, ordering,
      and refs; parent count and publication sequence; author and committer name
      and email; tag, candidate, acceptance, owner, actor, branch, conclusion, and
      event identity; and unexpected or missing paths. The trusted-launcher case
      must extract and execute the production launcher step/command from
      `.github/workflows/release.yml`, including immutable classifier extraction,
      instead of manually reproducing a similar launcher in test code.
  - id: REQ-004
    text: >
      The independent v0.1.5 publication proof must validate exact release-evidence
      schema and shape; the evidence commit's single-parent identity, automation
      author/committer, exact message, and sole versioned evidence path; the
      immutable candidate-derived content hash; owner artifact repository, commit,
      path, and byte hash; acceptance export and token paths, media type, subject
      bindings, and byte hashes; and every check command, result, subject, log ref,
      and log hash. The proof must be non-circular and must extract and execute the
      actual canonical-wordmark rule and positive/negative fixtures from the v0.1.5
      tag, demonstrating real dispatch polarity rather than trusting stored PASS
      text, candidate working-tree files, fixture byte presence, or the classifier's
      own verdict.
  - id: REQ-005
    text: >
      Publish only these review corrections as v0.1.5 with pack, ruleset, bundle
      release identity, protected fingerprints, workflow constants, commands,
      verifier expectations, logs, acceptance subject bindings, content hashes,
      owner hashes, and immutable release evidence synchronized to the same v0.1.5
      candidate. Preserve the complete canonical `./b backstop.sh` design and keep
      v0.1.3 at cb35c69e89844c5955d51b1b10e67da938010039 and v0.1.4 at
      71face4c4738b6652fb308348ab5676f2a056ff2. No Core edits, retagging, force
      push, waiver, weakened/skipped/vacuous check, unrelated rule change, or broad
      visual/release redesign is allowed.

claims:
  - id: CLM-001
    requirement: REQ-001
    text: The tagged canonical rule accepts exactly one visible exact-marker owner and rejects prefixed markers and concealment on either the owner or any component span.
    tests:
      - TestCanonicalWordmarkV015_AcceptsExactVisibleOwnerByDispatch
      - TestCanonicalWordmarkV015_RejectsPrefixedOwnerMarkerByDispatch
      - TestCanonicalWordmarkV015_RejectsOwnerAndComponentConcealmentByDispatch
  - id: CLM-002
    requirement: REQ-002
    text: Publication evidence content identity is derived from immutable package bytes and forged, stale, missing, or disconnected hashes and evidence cannot classify as authentic.
    tests:
      - TestReleaseClassifier_DerivesCandidatePackageContentHash
      - TestReleaseClassifier_RejectsForgedStaleAndMissingContentHashBindings
      - TestReleaseClassifier_RejectsForgedStaleAndMissingLogEvidenceBindings
  - id: CLM-003
    requirement: REQ-003
    text: Each mandated adversarial safety case exercises a distinct mutation and the trusted-launcher case executes the production workflow launcher extraction.
    tests:
      - TestReleaseWorkflow_AdversarialContentHashAndLogBindings
      - TestReleaseWorkflow_AdversarialCommandsResultsAndRefs
      - TestReleaseWorkflow_AdversarialParentsSequenceAndCommitIdentities
      - TestReleaseWorkflow_AdversarialTagCandidateAcceptanceOwnerAndEventIdentities
      - TestReleaseWorkflow_ExecutesExtractedProductionTrustedLauncher
      - TestReleaseWorkflow_MandatedCasesAreDistinctAndSubstantive
  - id: CLM-004
    requirement: REQ-004
    text: Independent v0.1.5 proof authenticates the complete evidence graph from immutable bytes and executes the tagged canonical rule against tagged positive and negative fixtures.
    tests:
      - TestReleaseV015_AuthenticatesEvidenceSchemaCommitAndPath
      - TestReleaseV015_AuthenticatesContentOwnerAcceptanceTokenAndLogs
      - TestReleaseV015_DispatchesTaggedCanonicalRuleAndFixtures
      - TestReleaseV015_ProofIsIndependentAndNonCircular
  - id: CLM-005
    requirement: REQ-005
    text: v0.1.5 synchronizes every release identity and proof surface while preserving the full wordmark, immutable v0.1.3/v0.1.4 tags, and the narrow repository fence.
    tests:
      - TestReleaseV015_VersionEvidenceAndHashesAreSynchronized
      - TestReleaseV015_PreservesCanonicalFullWordmark
      - TestReleaseV015_PreservesV013AndV014TagIdentity
      - TestReleaseV015_ReviewCorrectionChangeFence

contracts:
  - file: rules/design-system.yml
    provides:
      - name: canonical_wordmark
        kind: variable
        signature: "exact owner marker and visible ordered ./b, backstop, .sh components"
  - file: scripts/classify-release-publication.py
    provides:
      - name: authenticate_publication_evidence
        kind: function
        signature: "derive immutable package content identity and authenticate the complete publication evidence graph"
  - file: scripts/verify-release-workflow-safety.py
    provides:
      - name: adversarial_publication_matrix
        kind: function
        signature: "distinct identity, ancestry, content, evidence, and production-launcher cases"
  - file: scripts/verify-release-v015.py
    provides:
      - name: independent_v015_publication_proof
        kind: function
        signature: "independently authenticate evidence and dispatch tagged rule bytes against tagged fixtures"
  - file: pack.yml
    provides:
      - name: release_identity
        kind: constant
        signature: "backstop-ai/backstop-design-system v0.1.5 synchronized correction release"
---

# Correct v0.1.4 Independent Review Findings in v0.1.5

## Problem

Independent implementation review of published v0.1.4 found four concrete false
proof paths. First, `rules/design-system.yml` uses a word-boundary search for the
owner token, so `data-backstop-wordmark-foo` is accepted as the canonical marker.
Its structural lookahead rejects concealment attributes on the three spans but does
not reject `hidden` or `aria-hidden=true` on the owner itself, leaving a concealed
complete owner able to satisfy the contract. The fixture declaration does not
substantively dispatch exact-marker and owner/component concealment cases separately.

Second, `scripts/classify-release-publication.py` checks only that
`subject.content_hash` is 64 lowercase hex characters and then checks that the same
untrusted value is repeated elsewhere. It never derives that identity from the
immutable candidate or resolved package bytes. A consistently forged hash can
therefore authenticate, despite the classifier's otherwise detailed schema, owner,
acceptance, check, and log validation.

Third, `scripts/verify-release-workflow-safety.py` maps multiple mandated test names
to the same helper functions and collapses broad mismatch categories into a few
mutations. Its trusted-launcher test manually writes tagged classifier bytes to a
temporary path and calls the test helper; it does not execute the launcher from the
production workflow. PASS lines consequently overstate independent coverage of
hashes, logs, commands/results/refs, ancestry and sequence, commit identities, and
the complete release/event identity graph.

Fourth, `scripts/verify-release-v014.py` checks only a subset of the evidence graph.
It omits exact evidence schema/shape, evidence commit identity/message/path, owner
artifact/hash, acceptance and token hashes, and real tagged canonical-rule fixture
dispatch. Counting stored PASS text and checking fixture bytes does not independently
prove the tagged rule rejects the reviewed adversarial forms.

## Solution

Publish a focused v0.1.5 correction. Tighten the canonical owner match and add real
positive/negative dispatch fixtures for exact ownership and visibility. Bind the
classifier's content identity to immutable package bytes and make every evidence
edge fail closed. Replace aliased or partial workflow-safety cases with distinct
adversarial histories, and execute the actual production trusted launcher rather
than a test reimplementation. Add an independent v0.1.5 proof that authenticates the
full evidence graph and dispatches the rule and fixtures extracted from the tag.

Carry only the required version, fingerprint, workflow, owner, acceptance, log, and
evidence synchronization. The correction must preserve the canonical complete
wordmark and the immutable v0.1.3 and v0.1.4 releases; it must not alter Core or
redesign unrelated design-system or publication behavior.

## Verification

From candidate bytes, run `backstop pack check .`, `backstop pack test .`, the
public-site acceptance verifier, and the complete release-workflow safety verifier.
Fixture assertions must dispatch through the real canonical rule, and each mandated
safety test name must correspond to a distinct substantive scenario.

After immutable v0.1.5 tagging and conventional log/evidence publication, run
`scripts/verify-release-v015.py` with the actual tag, candidate SHA, and evidence
commit. The proof must read tagged/candidate and publication-commit bytes directly,
derive content identity independently, execute tagged rule/fixture polarity, and
confirm locally and remotely that v0.1.3 and v0.1.4 retain their recorded commits.

## References

- Independent implementation review findings for published v0.1.4.
- `rules/design-system.yml`, canonical-wordmark owner matching and visibility.
- `fixtures/rules/valid/index.html` and canonical-wordmark negative fixtures.
- `scripts/classify-release-publication.py`, especially subject content-hash and
  evidence/log authentication.
- `scripts/verify-release-workflow-safety.py` and the production launcher in
  `.github/workflows/release.yml`.
- `scripts/verify-release-v014.py` and `release-evidence/v0.1.4.yml`.
- ISSUE-001 delivered the v0.1.3 complete-wordmark correction; ISSUE-002 delivered
  the v0.1.4 descendant-classifier correction. This issue addresses defects found
  only by independent review of their published v0.1.4 implementation.
- BUNDLE-001 remains the exploring general release charter and does not enumerate or
  resolve these concrete post-publication review defects.

### Existence-in-world check

Before filing, `issues/` and `bundles/` were searched. ISSUE-001 owns the already
published v0.1.3 wordmark correction, ISSUE-002 owns the already published v0.1.4
descendant-classifier correction, and BUNDLE-001 is the general exploring release
line. None owns correction of these independent findings discovered on published
v0.1.4, so ISSUE-003 is the focused reactive v0.1.5 owner.
