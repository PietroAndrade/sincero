# SINCERO MVP: the public launch

Status: draft, 2026-11-04. Builds on [prd.md](prd.md) and [roadmap.md](roadmap.md). Task
numbers refer to [tasks.md](../../tasks.md); **new** marks work with no task yet.

## Hypothesis

A buyer about to sign for an off-plan apartment who sees the real cost and the credit gap before
signing will change what they do: negotiate, put more cash in, pick another property or walk away.

The MVP has to answer one question for that buyer, in Portuguese or English, in the browser:

> "How much will this apartment really cost me, will the bank's credit cover the balance at
> handover, and how much cash would close the gap?"

Anything that doesn't help answer it waits.

## Success criteria (defined before launch)

| Criterion | Target | Measured by |
|---|---|---|
| Correct figures | RA shows 19.6% extra cost and a R$ 39,802.30 gap, in the browser and over the API | `@ui` scenarios (8.3) and the 54 scenarios over the wire (5.14) |
| Time to first result | ≤ 2 min from opening the app, starting from a preset | Playwright timing on the main path |
| Activation | ≥ 80% of sessions that open the form reach a result | Server-side counts (see Must have) |
| Cash ladder use | ≥ 30% of sessions with a gap > 0 run a cash ladder | Server-side counts |
| Feedback | At least 10 pieces of feedback in the first month | Feedback link |
| Stability | No `internal` error on the main path; simulation ≤ 200 ms on the CLI | Logs; CLI timing |

The 30% and 10-feedback targets are guesses to check after the first month, not commitments.

## Scope (MoSCoW)

### Must have: without these the launch has no value

**Engine and API (M5)**
- 5.3c presence rule; 5.4 service + revision 7; 5.5 rules in the `.proto`.
- 5.6 server skeleton (error mapping, health endpoint); 5.7 store.
- 5.8 create/get/result; 5.9 nodes and field list (the views read nodes, not the 180 KB payload).
- 5.10 comparisons and 5.11 what-ifs: the cash ladder's response is a what-if, which is a comparison.
- 5.12 cash ladder; 5.13 retire REST; 5.14 `ConnectGateway`; 5.17 CORS (public domain + localhost).
- **new** request size limit and rate limiting per client.

**Front-end (M6)**, in Portuguese and English (6.12 answered)
- 6.1 scaffold; 6.2 generated client; 6.3 input form; 6.4 presets.
- 6.5 cost breakdown: the real cost.
- 6.8 credit gap panel: the gap and the pro-soluto installment.
- 6.10 cash ladder view: how much cash closes the gap.
- 6.11 loading, error and field-level validation states.
- **new** disclaimer: one line under every result, both languages, with the assumptions it uses
  (INCC 7.0% a year, bank rate 10.26%, TR = 0). Wording still to approve (PRD §9).

**Proof (M8)**
- 8.1–8.3 Playwright `@ui` scenarios: simulate, cash ladder, validation message, against `make api`
  + Vite. Compare is in the scenario list of 8.3; it moves to Should with 6.9.

**Ship (M7 + launch)**
- 7.1–7.3 backend and frontend images and compose, single process.
- **new** hosting and domain decision, and a deployed instance.
- **new** server-side usage counts: simulations created, cash ladders run, refused requests. Counts
  only, no inputs, nothing personal (LGPD). Needed to measure the success criteria.
- **new** feedback link in the app (a form or an e-mail address).

### Should have: important, a workaround exists

- 6.6 timeline stacked bars. Workaround: the breakdown already shows the construction interest total.
- 6.7 SAC vs PRICE and minimum income. Workaround: SAC is the default and its figures are in the
  breakdown.
- 6.9 comparison table across properties. Workaround: simulate each one in turn.
- 5.15 service-level features (error codes, expiry, CORS headers); 5.16 service docs.
- 7.4 behave as a compose service; 7.5 compose instructions in the READMEs.
- **new** CI running unit, behave and `@ui` on every PR (the `pre-push` hook covers it until then).

### Could have: if time allows

- 9.1 + 9.2 live INCC (BCB/SGS series, 7.0% fallback). First extension after launch.
- Shareable link to a simulation (the id is already a content hash; it lives until its TTL).
- 8.4 Playwright as a compose service with screenshots in Allure.
- 3.3 Allure end to end; 3.4 PT/EN feature parity check; 4.3/4.4 cleanup.

### Won't have this time

- TR, MIP/DFI, admin fee (9.3–9.6); physical progress at signing (9.7–9.11); pro-soluto with
  interest (9.12–9.13); PDF/CSV export.
- Accounts, saved simulations across restarts, more than one process.
- Accessibility criteria (deferred 2026-11-04); public API docs for third parties.

## What the MVP is not

- **Not a prototype:** it is deployed, validated at the boundary, rate-limited and proven by
  Playwright. A buyer can rely on it for an estimate.
- **Not the full product:** three of the six planned views are in (breakdown, gap, cash ladder).
  The other three wait for feedback.

## Main path the MVP must support

1. The buyer opens the app and picks Portuguese or English.
2. They pick a preset or enter price, months remaining, down payment %, FGTS and pre-approved credit.
3. They see the real cost (list price + extra cost, with the breakdown) and the disclaimer.
4. They see the gap: pre-approved vs needed, and the pro-soluto installment if there is a gap.
5. They run a cash ladder and see which amount closes the gap.
6. An invalid input is named next to its field; a server error shows a message, never a blank
   screen.

## Release readiness checklist

- [ ] Every Must have item done and accepted against its definition of done in `tasks.md`.
- [ ] `make test` passes; the 54 scenarios pass through `ConnectGateway`; `@ui` scenarios pass.
- [ ] RA in the deployed app shows 19.6% and R$ 39,802.30, in both languages.
- [ ] No open bug on the main path.
- [ ] Simulation ≤ 200 ms on the CLI; rate limiting and request size limit tested.
- [ ] Disclaimer wording approved and shown under every result.
- [ ] Usage counts recorded, and the feedback link reaches the maintainer.
- [ ] READMEs (EN and PT) describe how to run the stack and where the public instance is.
- [ ] Rollback plan: the previous image tag redeploys with one command; the in-memory store means
      no data migration.
- [ ] Release notes drafted.

## Decisions still needed before launch

1. Disclaimer wording (PRD §9).
2. Hosting provider and domain.
3. Feedback channel: a form or an e-mail address.
4. Whether to record the success targets above (30% cash ladder use, 10 pieces of feedback) or set
   others.
