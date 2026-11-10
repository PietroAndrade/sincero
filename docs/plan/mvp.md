# SINCERO MVP: the public launch

Status: rewritten 2026-11-09 to [typescript-port.md](typescript-port.md) (P0.2), after the
[decision](../decisions/engine-in-the-browser.md) that the engine runs in the browser. Builds on
[prd.md](prd.md) and [roadmap.md](roadmap.md). Items are named as in [backlog.md](backlog.md).

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
| Correct figures | RA shows 19.6% extra cost and a R$ 39,802.30 gap, in the browser | Playwright (US-09) and the 54 scenarios through the engine (P2.1); the golden master (P1.3) against the Python engine's answers |
| Time to first result | ≤ 2 min from opening the app, starting from a preset | Playwright timing on the main path |
| Speed | First result ≤ 2 s on the Lighthouse phone profile; initial JavaScript ≤ 150 KB gzipped | The performance budget in CI (P4.2) |
| Activation | ≥ 80% of sessions that open the form reach a result | Usage counts (US-10), if D2 chooses an analytics service |
| Cash ladder use | ≥ 30% of sessions with a gap > 0 run a cash ladder | Usage counts (US-10) |
| Feedback | At least 10 pieces of feedback in the first month | Feedback link (US-11) |
| Stability | No uncaught error on the main path, in Chromium, Firefox and WebKit | Playwright (P5.1) |

The 30% and 10-feedback targets are guesses to check after the first month, not commitments. If D2
chooses no analytics, the activation and ladder targets cannot be measured and drop out.

## Scope (MoSCoW)

### Must have: without these the launch has no value

**The engine (E1)**
- P1.1–P1.6 the `engine/` package: workspace, golden master, ported unit tests, structured errors,
  cash-ladder rules.
- P2.1 the 54 scenarios on cucumber-js; P3.1 the Node CLI; P3.2 READMEs; P3.3 the golden update
  protocol.

**The web app (E2)**, in Portuguese and English
- 6.12 language decision; 6.1 scaffold; P4.1 engine integration.
- US-01 language; US-02 the form; US-03 presets; US-04 real cost; US-06 credit gap; US-07 cash
  ladder; US-08 errors.
- US-05 and D1: a disclaimer under every result, both languages, with the assumptions it uses
  (INCC 7.0% a year, bank rate 10.26%, TR = 0). Wording still to approve (PRD §9).
- P4.2 performance budget.

**Proof (E3)**
- 8.1, 8.2, US-09 Playwright on the main path; P5.1 the golden corpus in three browsers.

**Ship (E4)**
- D2 static host and domain; P6.1 CI; US-13 the public address; US-11 feedback link and D3; the
  release checklist.

### Should have: important, a workaround exists

- 6.6 timeline stacked bars. Workaround: the breakdown already shows the construction interest total.
- 6.7 SAC vs PRICE and minimum income. Workaround: SAC is the default and its figures are in the
  breakdown.
- 6.9 comparison table across properties, and its Playwright scenario. Workaround: simulate each one
  in turn.
- US-10 usage counts, if D2 chooses an analytics service. Without it the activation and ladder
  targets are not measured.

### Could have: if time allows

- P0.3 a preview of the proof of concept for 3–5 buyers, during phases 1 to 3.
- 9.1 + 9.2 live INCC (BCB/SGS series, 7.0% fallback), once the browser-call question is answered.
- A shareable link that encodes the input in the URL.
- The Allure report for cucumber-js.

### Won't have this time

- TR, MIP/DFI, admin fee (9.3–9.6); physical progress at signing (9.7–9.11); pro-soluto with
  interest (9.12–9.13); PDF/CSV export.
- Accounts, saved simulations, any server: the site is static and nothing leaves the device.
- A public API for third parties. The same engine can run on Node behind Connect when it is wanted
  ([how](typescript-port.md#a-public-api-later)).
- Accessibility criteria (deferred 2026-11-04).

## What the MVP is not

- **Not a prototype:** it is deployed, its figures are pinned by a golden master and 54 scenarios,
  and Playwright proves the main path in three browsers. A buyer can rely on it for an estimate.
- **Not the full product:** three of the six planned views are in (breakdown, gap, cash ladder). The
  other three wait for feedback.

## Main path the MVP must support

1. The buyer opens the site and picks Portuguese or English.
2. They pick a preset or enter price, months remaining, down payment %, FGTS and pre-approved credit.
3. They see the real cost (list price + extra cost, with the breakdown) and the disclaimer.
4. They see the gap: pre-approved vs needed, and the pro-soluto installment if there is a gap.
5. They run a cash ladder and see which amount closes the gap.
6. An invalid input is named next to its field, in the chosen language; if the engine cannot load,
   a message says so, never a blank screen.

## Release readiness checklist

- [ ] Every Must have item done and accepted against its "Done when" in the plan.
- [ ] `npm test` passes: unit, golden master (on Node 24) and the 54 scenarios; the Playwright suite
      passes in Chromium, Firefox and WebKit.
- [ ] RA on the public site shows 19.6% and R$ 39,802.30, in both languages.
- [ ] No open bug on the main path.
- [ ] The performance budget holds: initial JavaScript ≤ 150 KB gzipped, first result ≤ 2 s on the
      phone profile.
- [ ] Disclaimer wording approved and shown under every result.
- [ ] Feedback link reaches the maintainer; usage counts recorded, or D2 chose none.
- [ ] READMEs (EN and PT) describe how to run the tests and where the public site is.
- [ ] Rollback plan: the previous build redeploys with one command; there is no data to migrate.
- [ ] Release notes drafted.

## Decisions still needed before launch

1. Disclaimer wording (PRD §9), D1.
2. Static host, domain, and analytics or none, D2.
3. Feedback channel: a form or an e-mail address, D3.
4. Whether to record the success targets above (30% cash ladder use, 10 pieces of feedback) or set
   others.
