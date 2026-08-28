---
title: "Correct Post-Tag Publication Descendant Classification for v0.1.4"
schema_version: issue/v1

issue:
  id: ISSUE-002
  title: "Correct Post-Tag Publication Descendant Classification for v0.1.4"
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
    Correct the pack repository's release-publication classifier and focused safety
    fixtures so authentic post-tag log/evidence descendants remain terminal no-ops
    when regenerated outputs are byte-identical, then publish the correction as
    v0.1.4 without moving v0.1.3 or changing Core.
  package: backstop-ai/backstop-design-system

requirements:
  - id: REQ-001
    text: >
      The publication classifier must recognize a legitimate post-tag log or evidence
      descendant as `post-tag-noop` when it descends from the immutable candidate,
      follows the repository's exact GitHub Actions actor/author, parent-chain, and
      commit-message conventions, changes no path outside the allowed publication
      log/evidence set, and the complete set of required generated outputs has the
      expected content and hash identity. A required output inherited unchanged from
      the candidate because regeneration produced byte-identical bytes must be
      authenticated rather than required to appear spuriously in the commit diff.
  - id: REQ-002
    text: >
      Subset handling must not become a path-only allowlist or an arbitrary-subset
      bypass. The classifier must reject a descendant with a missing, stale, forged,
      or unexpected required output; a changed disallowed path; wrong actor, author,
      message, event metadata, ancestry, or parent sequence; or evidence that does
      not bind the immutable tag, candidate, logs, content hashes, and successful
      results required by the release contract. Genuine candidate mismatch rejection
      must remain fatal, including a new candidate after an existing tag and any
      manual-dispatch attempt against a different candidate.
  - id: REQ-003
    text: >
      Executable regression coverage must reproduce the observed publication shape:
      regenerate all five required logs with three outputs byte-identical to their
      candidate bytes, commit only the two logs whose bytes changed, and prove that
      descendant selects `post-tag-noop`. Targeted negative fixtures must prove that
      arbitrary changed-path subsets and content/hash, ancestry, identity, or
      convention mismatches remain fatal, while all prior release-workflow safety
      tests continue to pass without skips, waivers, or vacuous assertions.
  - id: REQ-004
    text: >
      Publish the narrowly corrected classifier as v0.1.4 under the repository's
      candidate CI, detached proof, immutable-tag, pack-check, pack-test, acceptance
      dispatch, and independent publication-proof conventions. The v0.1.4 release
      must preserve the complete canonical `./b backstop.sh` wordmark contract and
      prior safety coverage. Tag v0.1.3 must remain fixed at
      cb35c69e89844c5955d51b1b10e67da938010039; no retagging, force push, waiver,
      Core edit, unrelated design change, or weakening of release proof is allowed.

claims:
  - id: CLM-001
    requirement: REQ-001
    text: Authentic publication descendants are classified from immutable ancestry, conventions, allowed paths, and complete required output identity rather than an exact changed-path count.
    tests:
      - TestReleaseWorkflow_PostTagLogDescendantAllowsByteIdenticalOutputs
      - TestReleaseWorkflow_PostTagEvidenceDescendantAuthenticatesRequiredOutputs
  - id: CLM-002
    requirement: REQ-002
    text: Only complete authentic publication state is accepted; arbitrary subsets and genuine candidate or publication-identity mismatches remain fatal.
    tests:
      - TestReleaseWorkflow_RejectsArbitraryPublicationPathSubsets
      - TestReleaseWorkflow_RejectsPublicationContentAndIdentityMismatch
      - TestReleaseWorkflow_RejectsMismatchedExistingTag
  - id: CLM-003
    requirement: REQ-003
    text: A real temporary Git history reproduces the two-changed/three-unchanged log case and the full positive and negative classifier matrix executes substantively.
    tests:
      - TestReleaseWorkflow_RegeneratedFiveLogsWithTwoChangedIsTerminalNoOp
      - TestReleaseWorkflow_ClassifierRegressionMatrixRetainsPolarity
  - id: CLM-004
    requirement: REQ-004
    text: v0.1.4 preserves the canonical full-wordmark and safety contracts, binds passing release evidence to immutable candidate bytes, and leaves the immutable v0.1.3 tag unchanged.
    tests:
      - TestReleaseV014_ClassifierFixAndEvidenceAreBound
      - TestReleaseV014_PreservesCanonicalWordmarkContract
      - TestReleaseV014_PreservesV013TagIdentity

contracts:
  - file: scripts/classify-release-publication.py
    provides:
      - name: classify
        kind: function
        signature: "authenticate immutable-candidate publication descendants by ancestry, conventions, allowed paths, and required output content/hash identity"
  - file: scripts/verify-release-workflow-safety.py
    provides:
      - name: publication_descendant_regression_matrix
        kind: function
        signature: "real-history positive byte-identical regeneration case plus fatal arbitrary-subset and mismatch cases"
  - file: pack.yml
    provides:
      - name: release_identity
        kind: constant
        signature: "backstop-ai/backstop-design-system v0.1.4 preserving the complete canonical wordmark contract"
---

# Correct Post-Tag Publication Descendant Classification for v0.1.4

## Problem

The immutable v0.1.3 tag correctly points to candidate commit
`cb35c69e89844c5955d51b1b10e67da938010039` and must never move. Candidate CI,
detached proof, tag integrity, pack checks and tests, acceptance dispatch, and
independent publication proof all passed for that release. After tagging, the
conventional `Record v0.1.3 publication checks` commit
`bc241fa43ee152e68acfb7f7c3e8f6734ddc6838` regenerated five required log
outputs, but only two files appeared in the commit because the other three outputs
were byte-identical to bytes already present at the tagged candidate.

`scripts/classify-release-publication.py` authenticates a log descendant by
requiring its changed-path set to equal all five log paths. Git truthfully records
only changed bytes, so the legitimate two-path commit fails that exact-set test and
is reported as a fatal candidate mismatch instead of the terminal
`post-tag-noop`. This makes a successful, convention-compliant publication create a
false-fatal follow-up while conflating diff shape with complete output identity.

Simply changing equality to subset membership would be unsafe: an arbitrary or
partial bot-looking commit could pass without proving every required log and the
release evidence are the authentic outputs for the immutable candidate. The defect
is therefore confined to authenticating publication descendants when some generated
outputs are unchanged, not to relaxing candidate mismatch or publication evidence
requirements.

## Solution

Correct the classifier around the immutable candidate boundary. Authenticate the
permitted log/evidence commit sequence through candidate ancestry, exact automation
identity and messages, allowed changed paths, and the actual content/hash identity
of every required publication output, whether that output was changed by the commit
or inherited byte-for-byte. Keep unexpected paths, incomplete or forged output
state, malformed evidence, wrong ancestry or conventions, manual mismatches, and
genuine post-tag candidates fatal.

Add focused executable histories matching the observed v0.1.3 two-changed and
three-unchanged log commit, together with negative mutation cases. Carry only this
release-safety correction through v0.1.4 publication while retaining the complete
canonical-wordmark contract and all existing safety checks. Do not edit Core or
reopen, replace, or move v0.1.3.

## Verification

Run the pack checks, pack tests, public-site acceptance verifier, and release-workflow
safety verifier from candidate bytes. The safety verifier must construct real Git
histories for both the observed unchanged-output case and the negative classifier
matrix. v0.1.4 publication proof must additionally establish its immutable candidate
and evidence bindings and independently confirm that `v0.1.3^{commit}` remains
`cb35c69e89844c5955d51b1b10e67da938010039` locally and remotely.

## References

- Immutable v0.1.3 candidate/tag commit:
  `cb35c69e89844c5955d51b1b10e67da938010039`.
- Actual publication-log commit:
  `bc241fa43ee152e68acfb7f7c3e8f6734ddc6838`, changing only
  `release-evidence/logs/canonical-wordmark-v013-candidate.log` and
  `release-evidence/logs/release-workflow-safety.log`.
- `scripts/classify-release-publication.py`, especially the exact five-path
  `is_log_commit` predicate.
- `scripts/verify-release-workflow-safety.py` and its existing post-tag, mismatch,
  resume, ordering, dispatch, and command tests.
- ISSUE-001 and PLAN-ISSUE-001 established and published the complete canonical
  wordmark contract in v0.1.3; this issue does not reopen that delivered scope.
- BUNDLE-001 owns the general design-system release line but does not identify this
  concrete post-publication classifier defect.

### Existence-in-world check

Before filing, `issues/` and `bundles/` were searched for post-tag publication,
descendant, classifier, and v0.1.4 ownership. ISSUE-001 concerns the canonical
wordmark correction released in v0.1.3, and BUNDLE-001 is the general exploring
release charter. Neither owns this newly observed classifier defect, so ISSUE-002 is
the focused reactive owner.
