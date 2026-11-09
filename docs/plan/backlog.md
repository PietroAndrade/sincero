# SINCERO MVP backlog

Status: rewritten 2026-11-09 to [typescript-port.md](typescript-port.md) (P0.2). It replaces the
server backlog of 2026-11-04: the Connect service, its store, rate limiting and Docker are gone
([decision](../decisions/engine-in-the-browser.md)). The buyer stories stay, with their criteria,
except what a server brought. Items are named by the plan's ids (**P1.1**…) or, for work that
existed before, by the old task number (6.1, 8.1…). `tasks.md` is not tracked in this repository and
still describes the retired plan; this file is the backlog.

Points are relative (Fibonacci, 1 to 13). There is no velocity yet: measure it over the first five
items of E1 and plan from there.

RA, the reference case used in the criteria: R$ 440,000, 19 months remaining, 20% down payment,
R$ 13,000 FGTS, defaults for everything else. Figures come from the retired Python engine
(`git show python-engine-final:backend/cli.py`, run from a worktree of the tag) until the Node CLI
(P3.1) prints them.

## Ordered backlog

| # | Item | Epic | Type | Pts | Depends on |
|---|---|---|---|---|---|
| 1 | P0.1 Decision record: the engine runs in the browser | E0 | Decision | 2 | — **done 2026-11-09** |
| 2 | P0.2 Rewrite ROADMAP, mvp.md, backlog.md to the plan | E0 | Task | 1 | 1 — **this change** |
| 3 | P1.1 Workspace skeleton: npm workspaces, Node 24, strict tsconfig, vitest, `npm test`, hook | E1 | Enabler | 2 | 2 |
| 4 | P1.2 Move `engine-ts` into `engine/src`; public API | E1 | Enabler | 2 | 3 |
| 5 | P1.3 Golden master: corpus + the tag's digests, vitest check | E1 | Enabler | 3 | 4 |
| 6 | P1.4 Port the model's unit tests (`test_models`, `test_validators`, `test_views`) | E1 | Enabler | 3 | 4 |
| 7 | P1.5 Structured errors: `code`, `field`, `params` | E1 | Enabler | 3 | 4 |
| 8 | P1.6 Cash-ladder amount rules in the engine | E1 | Enabler | 2 | 4 |
| 9 | P2.1 cucumber-js runs the `.feature` files; support and steps ported; `test_support` ported | E1 | Enabler | 5 | 5 |
| 10 | P3.1 CLI in Node, same flags as `cli.py`; `test_cli_controller` ported | E1 | Enabler | 3 | 4 |
| 11 | P3.2 READMEs (EN/PT) for Node; mark `api-contract.md` and the Connect decision superseded | E1 | Task | 3 | 9, 10 |
| 12 | P3.3 Golden update protocol: `npm run golden:update` | E1 | Task | 1 | 5 |
| 13 | 6.12 `DECISION` record the language decision (PT + EN) | E2 | Decision | 1 | — |
| 14 | D1 `DECISION` disclaimer wording | E2 | Decision | 1 | — |
| 15 | 6.1 Scaffold `web/` (Vite + React), with a translation file | E2 | Enabler | 3 | 3, 13 |
| 16 | P4.1 Engine integration: errors → field marks and PT/EN text from `code`/`params` | E2 | Enabler | 2 | 7, 15 |
| 17 | US-01 Choose the language | E2 | Story | 2 | 15 |
| 18 | US-02 Describe my contract | E2 | Story | 8 | 16 |
| 19 | US-03 Start from a reference property | E2 | Story | 2 | 18 |
| 20 | US-04 See the real cost | E2 | Story | 5 | 18 |
| 21 | US-05 Know what the figures are | E2 | Story | 2 | 14, 20 |
| 22 | US-06 See the credit gap | E2 | Story | 3 | 18 |
| 23 | US-07 See what more cash changes | E2 | Story | 5 | 8, 22 |
| 24 | US-08 Understand what went wrong | E2 | Story | 2 | 16, 18 |
| 25 | P4.2 Performance budget in CI: JS ≤ 150 KB gzipped, first result ≤ 2 s on the phone profile | E2 | Enabler | 2 | 20 |
| 26 | 8.1 Playwright fixture (`@playwright/test`) | E3 | Enabler | 2 | 15 |
| 27 | 8.2 UI driver for the cucumber world | E3 | Enabler | 3 | 9, 18, 26 |
| 28 | US-09 Prove the main path in a browser | E3 | Story | 5 | 23, 24, 27 |
| 29 | P5.1 The golden corpus in Chromium, Firefox and WebKit, to the cent | E3 | Enabler | 2 | 5, 26 |
| 30 | D2 `DECISION` static host and domain; analytics or none | E4 | Decision | 2 | — |
| 31 | D3 `DECISION` feedback channel | E4 | Decision | 1 | — |
| 32 | P6.1 CI pipeline: typecheck, vitest, golden, cucumber-js, Playwright, budget, build, previews | E4 | Enabler | 3 | 25, 28 |
| 33 | US-10 Count usage without tracking people | E4 | Story | 3 | 30 |
| 34 | US-11 Send feedback | E4 | Story | 2 | 31, 15 |
| 35 | US-13 Reach SINCERO on its public address | E4 | Story | 3 | 30, 32 |
| 36 | Release: readiness checklist and release notes | E4 | Task | 2 | all above |

Optional, any time after item 2: **P0.3** publish the proof of concept on a free static host as a
preview for 3–5 buyers (1 pt).

Plan total **97 points** against the 123 of the server backlog; P0.1 is done and P2.2 (CI running the
features twice) no longer applies, because Python left first. Decisions (13, 14, 30, 31) are cheap and
can be taken any time before the item that needs them.

## Epics

| Epic | Goal | Items |
|---|---|---|
| **E0. Decide** | The direction is recorded and the plan documents agree with it | 1–2 |
| **E1. The engine in TypeScript** | A package whose figures are the Python engine's to the bit, pinned by a golden master and by the 54 scenarios, with a CLI | 3–12 |
| **E2. Simulate in the browser** | A buyer gets the real cost, the gap and the cash ladder, in PT or EN, with no server | 13–25 |
| **E3. Prove the main path** | A browser test fails whenever the main path breaks, in three browsers | 26–29 |
| **E4. Ship and learn** | The site is public, measured without tracking people, and users can talk back | 30–36 |

## E1. The engine in TypeScript

Enabler items. Their acceptance test is the "Done when" column of the plan's phases 1 to 3; it is not
repeated here. The value they carry for the buyer is the gate to E2: the UI shows what the engine
computes, and G1 and G2 prove that is what the Python engine computed.

- **G1** (after item 8): golden 100% on Node 24; unit tests green; 54/54 through the package; a
  planted naive `sum()` fails the golden test.
- **G2** (after item 9): 54/54 on cucumber-js; the `(k − 1)/N` mutant fails 8 scenarios there too.

## E2. Simulate in the browser

### US-01 Choose the language (2 pts)

As a buyer, I want to use SINCERO in Portuguese or English, so that I understand every figure and
label.

- **AC1.** Given I open the app for the first time, When my browser prefers Portuguese, Then the app
  is in Portuguese; otherwise it is in English.
- **AC2.** Given the app is open, When I switch the language, Then every label, message and the
  disclaimer change, and the values I typed stay.
- **AC3.** Given I switched the language, When I come back later in the same browser, Then the app
  opens in the language I chose.
- **AC4.** Given either language, When an amount is shown, Then it is formatted as BRL
  (`R$ 440.000,00`).

### US-02 Describe my contract (8 pts)

As a buyer, I want to enter the terms of the contract I'm about to sign, so that the simulation is
about my apartment and not a generic one.

- **AC1.** Given the form, When I look at it, Then I can enter price, months **remaining** until
  delivery, down payment %, FGTS, cash at signing, pre-approved credit and developer installment,
  and every other input is reachable under "more options".
- **AC2.** Given the months field, When I read its label, Then it says months remaining until
  delivery, not the project's duration.
- **AC3.** Given I want balloon payments, When I add them, Then I choose the months only and never
  type an amount.
- **AC4.** Given the market assumptions, When the form opens, Then INCC is 7.0% a year and the bank
  rate 10.26% a year, and both can be changed.
- **AC5.** Given I submit RA, When the result arrives, Then the result appears without reloading the
  page and the form keeps my values.
- **AC6.** Given the same input entered twice, When the result is shown, Then the figures are the
  same. (There are no simulation ids: nothing is stored.)

Splits if it is too big: AC1–AC2 + AC5 first (the core fields), then AC3, then AC4 and "more options".

### US-03 Start from a reference property (2 pts)

As a buyer who wants to see how it works, I want to load an example property, so that I see a
result before typing my own numbers.

- **AC1.** Given the form, When I pick one of SO, F, SV, F4 or RA, Then the form fills with that
  property's price and months remaining.
- **AC2.** Given a preset is loaded, When I change any field, Then my change is kept and submitted.
- **AC3.** Given I pick RA and submit, When the result arrives, Then it is the RA result.

### US-04 See the real cost (5 pts)

As a buyer, I want to see what I'll pay on top of the list price before the first bank installment,
and why, so that I can judge the offer.

- **AC1.** Given RA, When the result is shown, Then I see R$ 86,155 (19.6%) on top of the list price.
- **AC2.** Given the result, When I look at the breakdown, Then I see each cost (INCC correction,
  construction interest, ITBI, registry) and the items add up to the total.
- **AC3.** Given a cost is zero, When the breakdown is shown, Then it is listed as zero, not hidden.
- **AC4.** Given a phone-width screen, When the result is shown, Then the breakdown reads without
  horizontal scrolling.

### US-05 Know what the figures are (2 pts)

As a buyer, I want to know the result is an estimate and what it assumes, so that I don't mistake it
for a bank quote.

- **AC1.** Given any result, When it is shown, Then a line under it says it is an estimate, in the
  approved wording (D1), in the current language.
- **AC2.** Given the result, When I read the line, Then it lists the INCC rate, the bank rate and
  TR = 0 that the simulation used, including any value I changed.
- **AC3.** Given no result yet, When I look at the form, Then no disclaimer is shown.

### US-06 See the credit gap (3 pts)

As a buyer with a pre-approved loan, I want to know whether the bank's credit will cover the
balance at handover, so that I am not caught short at the keys.

- **AC1.** Given RA, When the result is shown, Then I see pre-approved and needed credit side by
  side and a gap of R$ 39,802.30.
- **AC2.** Given there is a gap, When I look at the panel, Then I see the pro-soluto installment
  that would cover it.
- **AC3.** Given a pre-approval above the needed amount, When the result is shown, Then the panel
  says there is no gap and shows no pro-soluto.

### US-07 See what more cash changes (5 pts)

As a buyer with savings, I want to see what happens if I put more cash in at signing, so that I
know how much cash makes a difference.

- **AC1.** Given a result, When I enter cash amounts (for example 0, 30,000, 75,000, 100,000), Then I
  see one row per amount with the developer installment, the gap and the change in total cost
  against the base.
- **AC2.** Given RA and those amounts, When the rows are shown, Then the developer installment drops
  to zero at 75,000 while the gap stays at R$ 39,802.30, and at 100,000 the gap drops to
  R$ 36,975.43.
- **AC3.** Given the rows, When cash only pays the developer, Then the view says so: cash reduces the
  financed balance only after the down payment is covered.
- **AC4.** Given amounts that are unsorted, repeated or negative, When I run the ladder, Then the
  offending amount is named and no row is shown. (The rule lives in the engine, P1.6.)
- **AC5.** Given an amount above the list price, When I run the ladder, Then that amount is named as
  refused.

### US-08 Understand what went wrong (2 pts)

As a buyer, I want to know what to fix when something fails, so that I'm never stuck on a blank
screen.

- **AC1.** Given a required field is empty, When I submit, Then the field is marked and says it is
  required.
- **AC2.** Given FGTS plus cash above the list price, When I submit, Then the model's message is
  shown in the current language, built from the error's `code` and `params` (P1.5), and the form
  keeps my values.
- **AC3.** Given the engine fails to load, When the page opens, Then I see a message and a way to
  try again, never a blank screen.

The server cases of the old story (slow, unreachable, rate-limited) disappeared with the server.

## E3. Prove the main path

### US-09 Prove the main path in a browser (5 pts)

As the maintainer, I want the main path tested in a real browser, so that I know before a release
that a buyer can still get a result.

- **AC1.** Given the built site served locally, When `npm run e2e` runs, Then the simulate, cash
  ladder and validation scenarios pass.
- **AC2.** Given RA through the UI, When the scenario reads the result, Then it sees 19.6% and
  R$ 39,802.30, the same figures as the engine.
- **AC3.** Given a plain `npm test`, When it runs, Then no browser starts.
- **AC4.** Given the main path from a preset, When the scenario measures it, Then the result is shown
  in under 2 minutes of scripted use (in practice, seconds).

The compare scenario moves to Should with 6.9.

## E4. Ship and learn

### US-10 Count usage without tracking people (3 pts)

As the maintainer, I want to count how the app is used, so that I can check the MVP's success
criteria, without sending any input anywhere.

- **AC1.** Given a result is shown or a cash ladder runs, When it happens, Then a counter for that
  event goes up, through the service chosen in D2, or the story is dropped if D2 chooses none.
- **AC2.** Given the counters, When I read them, Then I get totals per day.
- **AC3.** Given any counted event, When it is recorded, Then no input value, IP address or other
  personal data is sent.
- **AC4.** Given the counters, When I compute activation and cash-ladder use, Then the numbers in
  `mvp.md`'s success criteria can be derived from them.

### US-11 Send feedback (2 pts)

As a buyer, I want to tell the maintainer what was wrong or missing, so that the next version fits
my case.

- **AC1.** Given any screen, When I look for it, Then a feedback link is visible in both languages.
- **AC2.** Given I follow it, When I send feedback, Then it reaches the maintainer through the
  channel chosen in D3.
- **AC3.** Given I send feedback, When it is sent, Then my simulation inputs are not attached unless
  I add them myself.

### US-13 Reach SINCERO on its public address (3 pts)

As a buyer, I want to open SINCERO at a public address, so that I can use it without installing
anything.

- **AC1.** Given the domain chosen in D2, When I open it over HTTPS, Then the app loads.
- **AC2.** Given the deployed app, When I simulate RA in either language, Then I see 19.6% and
  R$ 39,802.30.
- **AC3.** Given a new build, When it is deployed, Then the previous build can be redeployed with
  one command.

## Decisions

Each is done when the choice and its reason are recorded in `docs/decisions/`.

| Id | Decision | Needed before |
|---|---|---|
| 6.12 | Interface language: PT + EN (answered; record it) | 6.1 |
| D1 | Disclaimer wording, both languages | US-05 |
| D2 | Static host, domain, and analytics or none | US-10, US-13 |
| D3 | Feedback channel: a form or an e-mail address | US-11 |

## What left the backlog

Dropped with the server, see the [decision](../decisions/engine-in-the-browser.md): 5.5–5.14 (rules in
the `.proto`, server, store, RPCs, REST retirement, `ConnectGateway`), 5.17 and US-12 (CORS and abuse
protection), 7.1–7.3 (images and compose). Replaced: 6.2 (generated API client) by P4.1. Done before
the pivot and kept in history, with the tag: 5.3c and 5.4.

## After the MVP (not ordered)

**Should:** 6.6 timeline, 6.7 SAC vs PRICE, 6.9 comparison table (with the compare Playwright
scenario), the Allure report for cucumber-js (`allure-cucumberjs`).

**Could:** 9.1–9.2 live INCC (first check that the Banco Central's SGS API allows browser calls), a
shareable link that encodes the input in the URL, 4.3/4.4 are void (they were Python housekeeping).

## Backlog health

- Items 3–12 (E1) are refined: each has a "Done when" in the plan.
- E2 stories need refinement before 6.1 starts. Open points: the "more options" grouping in US-02,
  and whether US-07 suggests amounts or lets the buyer type them.
- Until P1.1 there is no test suite on `develop`; phase 1 starts next.
- Re-estimate after the first five items, once there is a velocity.
