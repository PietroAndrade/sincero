# SINCERO product roadmap

Status: rewritten 2026-11-09 to [typescript-port.md](typescript-port.md) (P0.2). Built from
[prd.md](prd.md), [ROADMAP.md](../../ROADMAP.md) and [backlog.md](backlog.md). `ROADMAP.md` is the
phase tracker; this file groups the same work by theme and order. The server roadmap of 2026-11-04
(Connect API, Docker, rate limiting) was retired with the
[decision](../decisions/engine-in-the-browser.md).

## Time horizon

No dates. The horizons are **gates**: work in a horizon starts when the gate before it is passed.

| Horizon | Gate to enter | Confidence |
|---|---|---|
| **Now** | — (in progress) | High: items written with a "Done when" |
| **Next** | **G2**: the 54 scenarios pass on cucumber-js against the TypeScript engine, and the golden master is 100% on Node 24 (G1) | Medium: stories written, UI details will move |
| **Later** | **G3**: RA in the browser shows 19.6% and R$ 39,802.30, in PT and EN | Low: direction and outcomes, scope to refine |

## Strategic themes

| Theme | Objective | Persona | Metric it moves |
|---|---|---|---|
| **T1. Trustworthy numbers** | Every figure is right and explainable | All buyers, advisors | Golden master and scenarios matching the Python engine's answers (100%) |
| **T2. Buyer experience** | A buyer gets the real cost and the gap without a terminal, in PT or EN, on a phone | First-time buyer, comparer | Time to first result ≤ 2 min; first result ≤ 2 s on the phone profile; activation ≥ 80% |
| **T3. Quality and delivery** | Each change is proven end to end and ships by publishing static files | Maintainer | Suites green in CI; performance budget held |
| **T4. Public reach** | People find, trust and share the tool | Public | Activation, shared links, returning users |

## Roadmap (theme × horizon)

| Theme | Now | Next | Later |
|---|---|---|---|
| **T1. Trustworthy numbers** | P1.1–P1.6 the `engine/` package with its golden master and structured errors; P2.1 scenarios on cucumber-js; P3.1–P3.3 CLI, READMEs, golden update protocol | 9.1 research: can the SGS API be called from a browser (CORS)? | 9.2 live INCC with 7.0% fallback; 9.3–9.6 TR, MIP/DFI, admin fee; 9.7–9.11 physical progress; 9.12–9.13 pro-soluto with interest |
| **T2. Buyer experience** | — | 6.12 language decision; D1 disclaimer; 6.1 scaffold, P4.1, US-01–US-08 (PT + EN) | 6.6–6.9 timeline, SAC vs PRICE, comparison; PDF/CSV export; shareable link in the URL |
| **T3. Quality and delivery** | P0.2 plan rewrite (this change); P0.3 optional preview | P4.2 budget; 8.1, 8.2, US-09 Playwright; P5.1 three browsers | P6.1 CI pipeline |
| **T4. Public reach** | — | — | D2 host and domain; US-10 counts (or none); US-11 feedback; US-13 public address; release |

## Order inside each horizon

**Now: the engine package, then the specification.** P0.2 → P1.1 → P1.2 → P1.3 → P1.4 → P1.5 → P1.6
(**G1**) → P2.1 (**G2**), with P3.1–P3.3 after P1.2. P0.3 (a preview for 3–5 buyers) can run
alongside to bring feedback in early.

**Next: the web app, then Playwright.** 6.12 and D1 are recorded first, because the PT + EN labels
shape the form. Then 6.1 → P4.1 → US-01 → US-02 → US-03 → US-04…US-07 → US-08 → P4.2 (**G3**), then
8.1 → 8.2 → US-09 → P5.1.

**Later: ship and extend.** D2, D3, P6.1, US-10, US-11, US-13, the release. The M9 extensions follow,
live INCC first. Each one has its own `DECISION` gate and can be reordered by value.

## Key milestones and decision points

| Milestone | What proves it | Decision needed before it |
|---|---|---|
| **G1. Engine proven** | Golden 100% on Node 24; unit tests green; 54/54 through the package; a planted naive `sum()` fails | — (P0.1 answered A–F) |
| **G2. Specification in TypeScript** (gate to Next) | cucumber-js 54/54; the `(k − 1)/N` mutant fails 8 scenarios | — |
| **G3. UI usable** (gate to Later) | RA in the browser shows 19.6% extra cost and a R$ 39,802.30 gap, in PT and EN | 6.12 language (answered: both); D1 disclaimer wording |
| **D. Main path proven** | US-09 and P5.1: the scenarios and the golden corpus pass in Chromium, Firefox and WebKit | — |
| **F. Public launch** | The site is reachable on its domain, with the disclaimer, within the budget | D2 host, domain, analytics; D3 feedback |
| **H. Live INCC** | 9.2: the simulation uses the 12-month index, with source and date shown; outage falls back to 7.0% | 9.1 source, terms and browser access |

## Resource implications

- **People:** one developer working with coding agents. Each item is sized for one PR through
  `/finish-task`, so the work stays sequential inside a horizon; only research (9.1) runs in parallel.
- **New skills by horizon:** Now: TypeScript, vitest, cucumber-js, floating-point details (Neumaier
  `sum`, round-half-even). Next: React, i18n, Playwright, a small charting library. Later: static
  hosting and CI.
- **Running costs:** none until F, then a domain; a static host is free at this scale. The BCB/SGS
  INCC data is free; FGV Dados is paid and not needed.
- **Translation:** every UI string in two languages from 6.1 on, and the Gherkin already exists in
  both.

## Assumptions

- The engine's figures are correct and stay pinned by the 54 scenarios and, after the port, by the
  golden master generated from the tag `python-engine-final`.
- The page's speed comes from its size (12.9 KB of engine); the budget in CI keeps it.
- The BCB republishes INCC under terms that allow a public app to use it with attribution (9.1
  confirms this).
- No accounts and no server: a simulation exists only in the page, and the input can be encoded in
  the URL to share it.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| No test suite on `develop` until P1.1 | A scenario is edited without being run | Phase 1 starts next; no scenario changes before G2 except for a bug the port finds |
| JavaScript engines disagree in the last bit (Node 22 vs 24) | Golden gate flaky | Node ≥ 24 pinned for the bit-exact gate; browsers checked to the cent (P5.1) |
| The golden master is generated from the tag, a different checkout | Digests drift from the engine they are meant to pin | Generate once in a worktree of `python-engine-final`; commit the digests; later changes need a scenario and a reviewed diff |
| Two languages from day one slow the UI | The web phase takes longer | Translation file from 6.1; Gherkin PT text as a glossary |
| Playwright slow or flaky | Gate D slips | Four main-path scenarios only; screenshots on failure |
| The page grows and loses its speed | The phone-first promise breaks | Performance budget in CI (P4.2); no Plotly |
| Safari and Firefox behave differently (untested) | Wrong cents in some browsers | P5.1 before launch |
| INCC series codes, terms or CORS differ from what was found | 9.2 waits | 7.0% fallback stays; a scheduled build can bake the index into the site; 9.1 is research before any code |
| Users read estimates as a quote | Trust and legal exposure | Disclaimer with the assumptions next to every result |
