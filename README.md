# Backstop Design System

Backstop's design system is distributed as executable policy rather than a
reference document. The pack owns three things together:

- named visual tokens;
- deterministic recipes that scaffold the canonical Jekyll foundation and
  landing page;
- rules with fixtures that prevent the scaffolded guarantees from drifting.

## Recipes

`jekyll-foundation@1.0.0` creates the token source, product stylesheet, and
favicon under `docs/`.

`jekyll-landing-page@1.0.1` creates the Jekyll layout and landing page under
`docs/`.

Both recipes are create-only. They produce known-good starting points without
silently merging into consumer-owned files.

## Enforced decisions

- Product CSS consumes the released `assets/design-system-tokens.css` asset.
- HTML does not bypass the system with inline styles.
- The canonical stylesheet retains visible keyboard focus and reduced-motion
  behavior.
- One marked canonical wordmark owner retains source-visible `./b`, `backstop`,
  and `.sh` elements in order.
- Every field-guide shell retains named navigation and a main landmark.
- Every rendered page uses the shared page-hero treatment exactly once.

`contracts/public-site-acceptance.yml` binds these seven rules to production
paths, deterministic mutations, owner fixtures, and dispatch evidence for
downstream actual-site acceptance.

Every rule carries a compliant fixture and a targeted violation fixture. Run
`backstop pack test .` to prove both sides of each claim.
