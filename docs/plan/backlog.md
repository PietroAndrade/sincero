# SINCERO MVP backlog

Status: draft, 2026-11-04. The backlog for [mvp.md](mvp.md), ordered: work from the top. Task numbers
refer to [tasks.md](../../tasks.md), whose definitions of done stay the acceptance test for enabler
items; user stories below carry their own Given/When/Then criteria. **new** marks items with no task
in `tasks.md` yet.

Points are relative (Fibonacci, 1 to 13). There is no velocity yet: measure it over the first five
items of E1 and plan from there.

RA, the reference case used in the criteria: R$ 440,000, 19 months remaining, 20% down payment,
R$ 13,000 FGTS, defaults for everything else. Figures from
`python cli.py --price 440000 --months 19 --fgts 13000`.

## Ordered backlog

| # | Item | Epic | Type | Pts | Depends on |
|---|---|---|---|---|---|
| 1 | 5.3c Presence rule on the real input | E1 | Enabler | 3 | — |
| 2 | 5.4 `service Simulations` + contract revision 7 | E1 | Enabler | 5 | 1 |
| 3 | 5.5 Model rules in the `.proto` | E1 | Enabler | 5 | 2 |
| 4 | 5.6 Server skeleton and error mapping | E1 | Enabler | 5 | 2 |
| 5 | 5.7 Simulation store | E1 | Enabler | 3 | — |
| 6 | 5.8 Create, get and read a simulation | E1 | Enabler | 5 | 3, 4, 5 |
| 7 | 5.9 Nodes and field list | E1 | Enabler | 5 | 6 |
| 8 | 5.10 Comparisons | E1 | Enabler | 5 | 6 |
| 9 | 5.11 What-ifs | E1 | Enabler | 5 | 8 |
| 10 | 5.12 Cash ladder | E1 | Enabler | 3 | 9 |
| 11 | 5.17 `DECISION` CORS origins: public domain + localhost | E3 | Decision | 1 | — |
| 12 | 5.13 Retire the REST layer | E1 | Tech debt | 2 | 10 |
| 13 | 5.14 `ConnectGateway`: the 54 scenarios over the wire | E1 | Enabler | 5 | 10 |
| 14 | **new** US-12 Protect the service from abuse | E3 | Story | 3 | 4 |
| 15 | 6.12 `DECISION` record the language decision | E2 | Decision | 1 | — |
| 16 | **new** D1 `DECISION` disclaimer wording | E2 | Decision | 1 | — |
| 17 | 6.1 Scaffold the front-end, with a translation file | E2 | Enabler | 3 | 15 |
| 18 | 6.2 Generated API client and error wrapper | E2 | Enabler | 3 | 13, 17 |
| 19 | US-01 Choose the language | E2 | Story | 2 | 17 |
| 20 | US-02 Describe my contract | E2 | Story | 8 | 18 |
| 21 | US-03 Start from a reference property | E2 | Story | 2 | 20 |
| 22 | US-04 See the real cost | E2 | Story | 5 | 20 |
| 23 | US-05 Know what the figures are | E2 | Story | 2 | 16, 22 |
| 24 | US-06 See the credit gap | E2 | Story | 3 | 20 |
| 25 | US-07 See what more cash changes | E2 | Story | 5 | 24 |
| 26 | US-08 Understand what went wrong | E2 | Story | 3 | 20 |
| 27 | 8.1 Playwright fixture | E4 | Enabler | 2 | 17 |
| 28 | 8.2 `UiGateway` | E4 | Enabler | 3 | 27, 20 |
| 29 | US-09 Prove the main path in a browser (8.3) | E4 | Story | 5 | 25, 26, 28 |
| 30 | **new** D2 `DECISION` hosting provider and domain | E5 | Decision | 2 | — |
| 31 | **new** D3 `DECISION` feedback channel | E5 | Decision | 1 | — |
| 32 | 7.1–7.3 Images and compose, single process | E5 | Enabler | 5 | 13, 17 |
| 33 | **new** US-10 Count usage without tracking people | E5 | Story | 3 | 6 |
| 34 | **new** US-11 Send feedback | E5 | Story | 2 | 31, 17 |
| 35 | **new** US-13 Reach SINCERO on its public address | E5 | Story | 5 | 30, 32, 14 |
| 36 | **new** Release: readiness checklist and release notes | E5 | Task | 2 | all above |

Must have total: **123 points**. Should and Could items are listed at the end, unordered until the
MVP ships.

Decisions (11, 15, 16, 30, 31) are cheap and can be taken any time before the item that needs them.
Taking them early removes waiting later.

## Epics

| Epic | Goal | Items |
|---|---|---|
| **E1. API on the wire** | The engine is reachable over Connect, validated at the boundary, and the 54 scenarios pass through it | 1–10, 12, 13 |
| **E2. Simulate in the browser** | A buyer gets the real cost, the gap and the cash ladder, in PT or EN | 15–26 |
| **E3. Protect the public service** | The public instance stays up and refuses abuse | 11, 14 |
| **E4. Prove the main path** | A browser test fails whenever the main path breaks | 27–29 |
| **E5. Ship and learn** | The app is public, measured, and users can talk back | 30–36 |

## E1. API on the wire

Enabler items. Their acceptance test is the definition of done of the same task in `tasks.md`; it is
not repeated here. The value they carry for the buyer is the gate to E2: the UI can only show what
the service returns, and 5.14 proves the service returns what the engine computes.

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
- **AC6.** Given the same input submitted twice, When the result arrives, Then it is the same
  simulation (same figures, same id).

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
  offending amount is named and no row is shown.
- **AC5.** Given an amount above the list price, When I run the ladder, Then that amount is named as
  refused.

### US-08 Understand what went wrong (3 pts)

As a buyer, I want to know what to fix when something fails, so that I'm never stuck on a blank
screen.

- **AC1.** Given a required field is empty, When I submit, Then the field is marked and says it is
  required, and nothing is sent.
- **AC2.** Given FGTS plus cash above the list price, When I submit, Then the model's message is
  shown in the current language and the form keeps my values.
- **AC3.** Given the server is slow, When I submit, Then I see that the result is loading and cannot
  submit twice.
- **AC4.** Given the server fails or is unreachable, When I submit, Then I see a message and a way to
  try again, never a blank screen.
- **AC5.** Given I was refused for sending too many requests (US-12), When I see the message, Then it
  says to wait and try again.

## E3. Protect the public service

### US-12 Protect the service from abuse (3 pts) **new**

As the maintainer, I want the public instance to refuse oversized and excessive requests, so that
one client can't take it down for everyone.

- **AC1.** Given a request body above the size limit, When it arrives, Then it is refused before it
  is parsed, with `resource_exhausted` or `invalid_argument`.
- **AC2.** Given a client above the rate limit, When it sends another request, Then it is refused
  with `resource_exhausted` and a hint of when to retry.
- **AC3.** Given a cash ladder or comparison, When it counts against the limit, Then it counts as one
  request per simulation it creates.
- **AC4.** Given the limits, When I deploy, Then both are set from environment variables with safe
  defaults.
- **AC5.** Given normal use of the main path, When a buyer simulates and runs a ladder, Then no limit
  is hit.

## E4. Prove the main path

### US-09 Prove the main path in a browser (5 pts)

As the maintainer, I want the main path tested in a real browser, so that I know before a release
that a buyer can still get a result.

- **AC1.** Given `make api` and the Vite dev server running, When `behave --tags=@ui` runs, Then the
  simulate, cash ladder and validation scenarios pass.
- **AC2.** Given RA through the UI, When the scenario reads the result, Then it sees 19.6% and
  R$ 39,802.30, the same figures as the engine.
- **AC3.** Given a plain `make features`, When it runs, Then no browser starts.
- **AC4.** Given the main path from a preset, When the scenario measures it, Then the result is shown
  in under 2 minutes of scripted use (in practice, seconds).

The compare scenario of 8.3 moves to Should with 6.9.

## E5. Ship and learn

### US-10 Count usage without tracking people (3 pts) **new**

As the maintainer, I want to count how the app is used, so that I can check the MVP's success
criteria.

- **AC1.** Given a simulation is created, a cash ladder runs or a request is refused, When it
  happens, Then a counter for that event goes up.
- **AC2.** Given the counters, When I read them, Then I get totals per day.
- **AC3.** Given any counted event, When it is recorded, Then no input value, IP address or other
  personal data is stored.
- **AC4.** Given the counters, When I compute activation and cash-ladder use, Then the numbers in
  `mvp.md`'s success criteria can be derived from them.

### US-11 Send feedback (2 pts) **new**

As a buyer, I want to tell the maintainer what was wrong or missing, so that the next version fits
my case.

- **AC1.** Given any screen, When I look for it, Then a feedback link is visible in both languages.
- **AC2.** Given I follow it, When I send feedback, Then it reaches the maintainer through the
  channel chosen in D3.
- **AC3.** Given I send feedback, When it is sent, Then my simulation inputs are not attached unless
  I add them myself.

### US-13 Reach SINCERO on its public address (5 pts) **new**

As a buyer, I want to open SINCERO at a public address, so that I can use it without installing
anything.

- **AC1.** Given the domain chosen in D2, When I open it over HTTPS, Then the app loads.
- **AC2.** Given the deployed app, When I simulate RA in either language, Then I see 19.6% and
  R$ 39,802.30.
- **AC3.** Given a new image tag, When it is deployed, Then the previous tag can be redeployed with
  one command.
- **AC4.** Given the deployment, When the backend is checked, Then the health endpoint answers and
  one worker process runs.
- **AC5.** Given a browser on another origin, When it calls the API, Then CORS refuses it.

## Decisions

Each is done when the choice and its reason are recorded in `docs/decisions/`.

| Id | Decision | Needed before |
|---|---|---|
| 5.17 | CORS origins: public domain + localhost (answered; record it) | US-13 |
| 6.12 | Interface language: PT + EN (answered; record it) | 6.1 |
| D1 | Disclaimer wording, both languages | US-05 |
| D2 | Hosting provider and domain | US-13 |
| D3 | Feedback channel: a form or an e-mail address | US-11 |

## After the MVP (not ordered)

**Should:** 6.6 timeline, 6.7 SAC vs PRICE, 6.9 comparison table (with the compare `@ui` scenario),
5.15 service-level features, 5.16 service docs, 7.4–7.5 compose behave service and instructions,
CI on every PR.

**Could:** 9.1–9.2 live INCC, shareable links, 8.4 Playwright in compose, 3.3, 3.4, 4.3, 4.4.

## Backlog health

- Items 1–14 (E1, E3) are refined: each has a definition of done in `tasks.md`.
- E2 stories need refinement before 6.1 starts. Open points: the "more options" grouping in US-02,
  and whether US-07 suggests amounts or lets the buyer type them.
- Re-estimate after the first five items, once there is a velocity.
