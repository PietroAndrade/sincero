# SINCERO product roadmap

Status: draft, 2026-11-04. Built from [prd.md](prd.md), [ROADMAP.md](../../ROADMAP.md) and
[tasks.md](../../tasks.md). `ROADMAP.md` is the milestone tracker and `tasks.md` the task breakdown;
this file groups the same work by theme and order, and adds what the PRD asks for but no task covers
yet (marked **new**).

## Time horizon

No dates. The horizons are **gates**: work in a horizon starts when the gate before it is passed.

| Horizon | Gate to enter | Confidence |
|---|---|---|
| **Now** | — (in progress) | High: tasks written with a definition of done |
| **Next** | The API runs over Connect and all 54 behave scenarios pass through `ConnectGateway` (5.14) | Medium: tasks written, UI details will move |
| **Later** | The UI and its Playwright scenarios pass against the local processes (8.3) | Low: direction and outcomes, scope to refine |

## Strategic themes

| Theme | Objective | Persona | Metric it moves |
|---|---|---|---|
| **T1. Trustworthy numbers** | Every figure is right and explainable | All buyers, advisors | Scenarios matching independently computed figures (100%) |
| **T2. Public API platform** | A typed, validated service the UI and others can build on | Integrator | RPCs covering revision 6 of the contract; errors that name field and rule |
| **T3. Buyer experience** | A buyer gets the real cost and the gap without a terminal, in PT or EN | First-time buyer, comparer | Time to first result ≤ 2 min; activation ≥ 80% |
| **T4. Quality and delivery** | Each change is proven end to end and ships with one command | Maintainer | Suites green in CI; `docker compose up` on a fresh clone |
| **T5. Public reach** | People find, trust and share the tool | Public | Activation, shared links, returning users |

## Roadmap (theme × horizon)

| Theme | Now | Next | Later |
|---|---|---|---|
| **T1. Trustworthy numbers** | 5.3c presence rule on the real input (S); 5.5 model rules in the `.proto` (M) | 9.1 `DECISION` live INCC source: confirm SGS codes 192/7456 and the BCB terms (S) | 9.2 live INCC with 7.0% fallback (M); 9.3–9.6 TR, MIP/DFI, admin fee (L); 9.7–9.11 physical progress (L); 9.12–9.13 pro-soluto with interest (M) |
| **T2. Public API platform** | 5.4 `service Simulations` + contract revision 7 (M); 5.6 server skeleton (M); 5.7 store (M); 5.8–5.12 RPCs (L); 5.13 retire REST (S); 5.17 CORS: public domain + localhost (S) | **new** request size limit and rate limiting per client (S) | Public API docs for third parties (S), if anyone asks |
| **T3. Buyer experience** | — | 6.12 record the language decision (S); 6.1–6.11 React front-end, PT + EN (XL); **new** disclaimer line under every result (S) | PDF/CSV export (M); shareable links to a simulation (S, ids already are content hashes) |
| **T4. Quality and delivery** | 5.14 `ConnectGateway` (M); 5.15 service-level features (M); 5.16 service docs (S); 3.3 Allure end to end (S); 3.4 PT/EN feature parity check (S); 4.3/4.4 cleanup (S) | 8.1–8.3 Playwright `@ui` scenarios against `make api` + Vite (L) | 7.1–7.5 Docker compose (M); 8.4 Playwright as a compose service with screenshots (S); **new** CI running unit, behave and `@ui` (M) |
| **T5. Public reach** | — | — | **new** hosting and domain decision (S); **new** privacy-safe telemetry, counts only, LGPD (M); **new** public launch (M) |

Sizes: S ≈ one PR, M ≈ 2–4 PRs, L ≈ 5–8 PRs, XL ≈ a milestone.

## Order inside each horizon

**Now: finish the API (M5).** 5.3c → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9 → 5.10 → 5.11 → 5.12 →
5.13 → 5.14 → 5.15 → 5.16, with 5.17 any time before 5.15. The housekeeping tasks (3.3, 3.4, 4.3,
4.4) fit in between and block nothing.

**Next: UI first, then Playwright.** 6.12 is recorded first, because the PT + EN labels shape 6.3.
Then 6.1 → 6.2 → 6.3 → 6.4 → the views 6.5–6.10 → 6.11, then 8.1 → 8.2 → 8.3. The 9.1 decision is
research only and can run alongside.

**Later: ship and extend.** 7.1–7.5 and 8.4, then CI, hosting, telemetry and the launch. The M9
extensions follow, live INCC first. Each one has its own `DECISION` gate and can be reordered by
value.

## Key milestones and decision points

| Milestone | What proves it | Decision needed before it |
|---|---|---|
| **A. Contract fixed** | 5.4/5.5: the `.proto` compiles, revision 7 maps every row of revision 6, every rule has a failing test | — (5.3 accepted) |
| **B. API on the wire** (gate to Next) | 5.14: 54 scenarios pass through `ConnectGateway` | 5.17 CORS origins |
| **C. UI usable** | 6.3–6.11: RA in the browser shows 19.6% extra cost and a R$ 39,802.30 gap, in PT and EN | 6.12 language (answered: both); disclaimer wording |
| **D. UI proven** (gate to Later) | 8.3: `@ui` simulate, compare, cash ladder and validation scenarios pass | — |
| **E. One-command stack** | 7.3/7.5: `docker compose up` from a fresh clone serves the app | — |
| **F. Public launch** | The app is reachable on its domain, with rate limits and the disclaimer | Hosting provider, domain, telemetry approach |
| **G. Live INCC** | 9.2: the simulation uses the 12-month index, with source and date shown; outage falls back to 7.0% | 9.1 source and terms |

## Resource implications

- **People:** one developer working with coding agents. Each task is sized for one PR through
  `/finish-task`, so the work stays sequential inside a horizon; only research tasks (9.1) run in
  parallel.
- **New skills by horizon:** Now: Connect/`protovalidate`, ASGI. Next: React, TypeScript, Plotly,
  i18n, Playwright. Later: Docker, nginx, CI, hosting and operations.
- **Running costs:** none until F. Afterwards: one small host (single process, in-memory store) and
  a domain. The BCB/SGS INCC data is free; FGV Dados is paid and not needed.
- **Translation:** every UI string in two languages from 6.3 on, and the Gherkin already exists in
  both.

## Assumptions

- The engine's figures (M1–M4) are correct and stay pinned by the 54 scenarios.
- One process is enough for public traffic at launch; the store's capacity bounds memory.
- The BCB republishes INCC under terms that allow a public app to use it with attribution (9.1
  confirms this).
- No accounts: a simulation lives in memory until its TTL and is recovered by re-posting its input.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Presence rule (5.3c) breaks the `gen_dto.py` chain | Blocks every later M5 task | Small PR first; existing generator tests stay unedited |
| Behave over the wire is flaky (5.14) | The gate to Next never closes | Same scenarios, one switch; the engine run stays the default |
| Two languages from day one slow the UI | M6 takes longer | Translation file from 6.1; Gherkin PT text as a glossary |
| Playwright slow or flaky | The gate to Later slips | Four main-path scenarios only; screenshots on failure |
| Public traffic on one in-memory process | Memory spikes, lost simulations | Capacity + TTL, rate limiting; re-posting restores state |
| INCC series codes or terms differ from what was found | 9.2 waits | 7.0% fallback stays; 9.1 is a decision before any code |
| Users read estimates as a quote | Trust and legal exposure | Disclaimer with the assumptions next to every result |
