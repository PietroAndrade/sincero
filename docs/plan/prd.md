# PRD: SINCERO, from engine to product (draft)

Status: **draft for review**, 2026-11-04. Sources: `README.md`, `ROADMAP.md`, `tasks.md`,
`docs/decisions/`, and the ai-memory pages `decisions/api-contract-resource-model.md`,
`_rules/git-workflow.md` and the 2026-11-02 to 11-04 session logs.

## 1. Executive summary

SINCERO (*Simulador de Impacto do INCC no Custo pela Evolução Real da Obra*) shows a Brazilian
buyer what an off-plan (*na planta*) apartment really costs: INCC correction on everything still
owed, construction interest during the build, closing costs, SAC/PRICE installments after handover,
and the credit gap the bank opens at transfer (the "Caixa trigger"). It also shows what changes when
the buyer puts more cash in at signing. The calculation engine, CLI and executable specification
are done (milestones 1–4: 223 unit tests, 54 behave scenarios). This PRD covers the rest: a Connect
API (M5), a browser front-end (M6), packaging (M7), UI acceptance tests (M8) and domain extensions
(M9), so a buyer who doesn't use a terminal can run the simulation before signing a contract.

## 2. Problem statement

**Pain.** Developers quote a list price and a monthly installment. They don't quote:

- INCC correction on the remaining down payment and on the balance the bank will finance;
- construction interest (*juros de obra*) charged by the bank from signing to handover;
- ITBI and registry fees;
- the credit gap: at handover the corrected balance is usually higher than the pre-approved credit,
  and the buyer has to cover the difference in cash or through a pro-soluto.

Reference case (RA): R$ 440,000, 19 months to delivery, 20% down payment, R$ 13,000 FGTS. That comes
to **R$ 86,155 (19.6%) above the list price before the first bank installment**, and the bank has to
approve **R$ 39,802 more** than it pre-approved.

**Today.** Buyers use spreadsheets, the developer's sales simulation (which leaves INCC and
construction interest out), or the bank's simulator, which only covers the financing after handover.
No tool combines the construction phase, the handover and the bank phase on one month-by-month
timeline.

**Cost of not solving it.** The buyer finds the gap at handover, when the contract is already signed.
The options left are emergency cash, a pro-soluto with interest, or losing the apartment.

## 3. Goals and success metrics

| Goal | Metric | Target | When |
|---|---|---|---|
| G1. Correct numbers | Reference scenarios in the payload contract that match independently computed figures | 100% of the 54 scenarios, through the engine **and** over the wire (5.14) | End of M5 |
| G2. Usable without a terminal | A buyer simulates RA in the browser from a fresh `docker compose up` | ≤ 2 min from opening the app to a result; every `SimulationInput` field reachable | End of M7 |
| G3. Decision support | The buyer can compare properties and see what extra cash does | Comparison of the 5 presets plus a 4-rung cash ladder, matching the CLI figures | End of M6 |

AARRR. The tool is **public** (decided 2026-11-04) but has no business model yet, so only part of
AARRR applies:

- **Activation:** share of sessions that reach a first result (target ≥ 80%). This needs privacy-safe
  telemetry: counts only, no inputs, LGPD-compliant.
- **Retention:** returning users who run a comparison or a cash ladder after their first simulation.
- **Referral:** a simulation is addressable by a content-hash id, so a link can be shared. It only
  lives while the in-memory store keeps it (TTL).
- **Acquisition / Revenue:** out of scope for this PRD.

## 4. User personas

**Primary: the first-time off-plan buyer.** Middle-income, uses FGTS, pre-approved by Caixa or
another bank, about to sign with a developer.
- JTBD: "Before I sign, tell me the real total and whether the bank's credit will cover the balance
  at handover."
- JTBD: "Show me how much more cash at signing I'd need for the gap to disappear."

**Secondary: the buyer comparing properties.** Has 2–5 candidates with different prices and delivery
dates.
- JTBD: "Put these properties side by side on total cost, peak monthly outlay and gap."

**Tertiary: the advisor (real-estate broker, financial planner, relative).** Runs scenarios for
someone else.
- JTBD: "Change one assumption (INCC, bank rate, installment) and show what changes."

**Internal: the developer of the tool / integrator.** Consumes the API from the TypeScript client.
- JTBD: "A typed, generated client whose errors name the field and the rule."

## 5. Requirements

### 5.1 Functional

**Must have (M5–M7)**
- F1. Simulate one contract: every `SimulationInput` field, with the same results as
  `python cli.py … --json`.
- F2. Simulations are stored resources whose id is a hash of the resolved input, so creating is
  idempotent and posting again restores lost state (decision `api-contract-resource-model`).
- F3. Read the result whole, or only part of it, through a typed result with a `FieldMask`. The three
  schedules are 97% of the ~180 KB payload.
- F4. Comparisons by ids (1–20, order kept) and by base plus candidates (all-or-nothing, with the
  failing index).
- F5. What-if: a comparison relative to a base, with `overrides` and `delta` per row.
- F6. Cash ladder: finite, non-negative, strictly increasing absolute amounts; a rung above the list
  price is refused with its index.
- F7. Validation: a required field has explicit presence (`optional` + `buf.validate` `required`),
  so "absent" and "zero" are refused with different violations before the model runs. Model rules
  come back as `invalid_argument` with an `ErrorInfo` and the message verbatim.
- F8. Front-end: input form (months labelled **remaining**; balloon months chosen, never an amount),
  presets SO/F/SV/F4/RA, cost breakdown, timeline stacked bars with the peak marked, SAC vs PRICE
  with minimum income, credit gap panel, comparison table, cash ladder.
- F9. One-command local stack: `docker compose up` (backend, nginx front-end, healthcheck).

**Should have**
- F10. Service-level behave features: error codes, malformed requests, expiry, CORS (5.15).
- F11. UI acceptance scenarios with Playwright, with screenshots in Allure on failure (M8).
- F12. Portuguese/English parity check for the feature files (3.4).

**Nice to have (M9, ordered by value)**
- Live INCC from FGV with a 7.0% fallback; TR on the bank phase; MIP/DFI insurance and admin fee;
  physical progress at signing; pro-soluto with interest; PDF/CSV export.

### 5.2 Non-functional

- **Correctness:** months compound (`(1+r)^(1/12)-1`), month 0 is signing, bank installments start
  at N+1, balloon amounts are derived, and cash or FGTS at signing pays the developer first. These
  are pinned by the Gherkin spec and may not regress.
- **Performance:** a single simulation runs in under 200 ms, **measured on the CLI** (decided
  2026-11-04). This is the engine budget; network time is not part of it. Node reads avoid sending
  the 180 KB payload.
- **Security:** no PII is stored and no accounts exist. `internal` errors return a constant body,
  never a traceback (5.6). Unknown JSON fields are refused. CORS allows the public domain and
  localhost, configured in one place (5.17). Since the service is public, it also needs a request
  size limit and rate limiting per client.
- **Scalability:** a single process by design, because the store is in memory. The store's capacity
  bounds memory under public traffic. Documented as a constraint, not solved (7.1).
- **Maintainability:** `app/models` has no I/O, protobuf or Connect imports. Input fields are
  declared once in `.proto`, and a test fails on drift. Step definitions stay thin.
- **Accessibility:** deferred (2026-11-04). Fields are labelled and errors are shown next to their
  field (6.11); no WCAG criterion for now.
- **Localization:** BRL formatting; interface in **Portuguese and English** (6.12 decided
  2026-11-04), with a language switch. Every label and message comes from a translation file.

### 5.3 Out of scope

- User accounts, saved portfolios, persistence across restarts.
- Bank or developer integrations (credit pre-approval, contract import).
- Horizontal scaling or a shared store.
- Legal or tax advice. The results are estimates under stated assumptions.
- A REST API: replaced by Connect, and the REST shape layer is retired in 5.13.

## 6. User flows

**Happy path (primary persona)**
1. Opens the app and picks a preset or enters price, months remaining, down payment %, FGTS and
   pre-approved credit.
2. Optionally sets the developer installment and balloon months.
3. Submits. The backend validates, simulates, stores and returns the id plus a summary.
4. Sees the extra cost over the list price, the timeline with the construction interest peak, and
   the credit gap.
5. Opens the cash ladder ("what if I put in R$ 30k / 75k / 100k more?") and sees the gap shrink.
6. Optionally compares with other candidate properties.

**Decision points**
- Gap > 0: cover it with cash (cash ladder), take a pro-soluto (installment shown), or change
  property (comparison).
- SAC vs PRICE: a higher first installment against a lower total. Minimum income is shown for both.

**Error states and recovery**
- Missing required field → violation naming the field next to the input; nothing is sent to the
  model.
- Model rule (e.g. FGTS + cash above the list price) → the model's message verbatim; the form keeps
  its values.
- Batch item invalid (comparison or ladder) → the failing index is highlighted; nothing is stored.
- Expired simulation id (`not_found`) → the client posts the input again; the id is a content hash,
  so it stays the same.
- Server fault → a constant `internal` message with a retry; never a blank screen (6.11).

## 7. Technical considerations

- **Architecture:** MVC, with dependencies pointing `controllers → views → models`. M5 adds a Connect
  service (`connectrpc` on `uvicorn`) as a new controller; `api_requests.py` is retired once
  `protovalidate` enforces the rules declared in the `.proto`.
- **Integration points:** one `.proto` generates the Python server and the TypeScript client
  (`protoc-gen-es` + `@connectrpc/connect-web`). Connect / gRPC-Web, no proxy. nginx proxies the
  service paths in M7.
- **Data:** inputs only, kept in memory keyed by a hash of the normalised input, with a TTL and LRU
  capacity (`SINCERO_SIMULATION_TTL_SECONDS`, `SINCERO_SIMULATION_CAPACITY`). Results are recomputed,
  not stored.
- **Migration:** `docs/api-contract.md` goes from revision 6 (REST) to revision 7 (RPCs): every REST
  row maps to an RPC and every error code to a Connect code. Flask is removed from the requirements.
  Behave gains a `ConnectGateway` behind a switch; the default run keeps `EngineGateway`.
- **Generation chain:** every `protoc` call has to resolve `buf/validate/validate.proto` (the
  generator, the experiments, `buf generate`, `generate.sh`). Task 5.3c is the first one this
  affects.

## 8. Timeline and milestones

| Phase | Deliverables (tasks) | Depends on | Main risk |
|---|---|---|---|
| P0. Housekeeping | 3.3 Allure end-to-end, 3.4 pt-BR parity check, 4.3/4.4 branch and root cleanup | — | Low |
| P1. Contract | 5.3c presence rule on the real input, 5.4 `service Simulations` + revision 7, 5.5 rules in the `.proto` | 5.3 ✅ | `optional` + `required` changes `gen_dto.py`; CEL cross-field rule |
| P2. Service | 5.6 skeleton and error mapping, 5.7 store, 5.8–5.12 RPCs | P1 | FieldMask projection on nested schedules; store thread safety |
| P3. Wire tests and cleanup | 5.13 retire REST, 5.14 `ConnectGateway`, 5.15 service features, 5.16 docs, 5.17 CORS | P2 | Suite flakiness over the wire |
| P4. Front-end (**top priority after P3**) | 6.1–6.11 in Portuguese and English (6.12 decided) | P3 done: the API runs over gRPC/Connect and all behave scenarios pass through `ConnectGateway` | Chart readability on mobile; two languages from day one |
| P5. UI acceptance (**next priority**) | 8.1–8.3 Playwright `@ui` scenarios against `make api` + the Vite dev server | P4 | Browser tests slow or flaky in CI |
| P6. Packaging | 7.1–7.5 compose stack, behave service, then 8.4 (Playwright as a compose service with Allure screenshots) | P4, P5 | Single-worker constraint missed in production-like setups |
| P7. Extensions | Live INCC first (see §9, item 7), then the other M9 items, each gated by its `DECISION` | P3 minimum | INCC source terms; regulatory rules (MIP/DFI) |

**Priority (decided 2026-11-04):** the UI starts as soon as the API runs smoothly over
gRPC/Connect with the BDD suite passing over the wire (end of P3). Playwright comes right after
the UI. Docker moves after Playwright: P5 runs the browser tests against the local processes, so
only 8.4 waits for compose. `ROADMAP.md` and `tasks.md` follow this order.

No dates are set. Each task is sized for one PR and goes through `/finish-task` (`feat/*` from
`develop`, squash-merge).

## 9. Decisions and open questions

Answered 2026-11-04:

1. **Audience:** public. Accounts stay out of scope.
2. **Interface language (6.12):** both Portuguese and English.
3. **CORS origins (5.17):** the public domain plus localhost for development.
4. **Performance target:** under 200 ms per simulation, measured on the CLI.
5. **Accessibility:** deferred.
6. **Disclaimer:** still open, see below.
7. **Live INCC:** checked, see below. It is the first M9 extension.
8. **Construction interest ceiling and pro-soluto rules (9.11, 9.12):** deferred.

**Still open: the disclaimer (item 6).** A public tool that shows financial figures should say what
they are: estimates based on the assumptions on screen (INCC 7.0% a year, bank rate 10.26%, TR = 0),
not an offer, a bank quote or financial advice. The question is only the wording and where it
appears: a short line under the result, the footer, or both. Proposed default: one line under every
result, in both languages, plus the assumptions listed next to it.

**Live INCC, what was found (2026-11-04).**
- The Banco Central's SGS API republishes FGV's INCC as open data, with no key:
  `https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json`. Series **192** returned
  monthly % changes up to 09/2026 and series **7456** up to 10/2026. These are most likely INCC-DI
  and INCC-M (INCC-M is released earlier in the month, which fits). Confirm the codes in 9.1.
- FGV's own database (FGV Dados) moved INCC to its paid Standard tier (IBRE *Conjuntura Estatística*,
  Dec 2024), so fetching from FGV directly needs a licence. The BCB republication is the practical
  source.
- Developer contracts usually index on INCC-DI or INCC-M. The input could name which one, with the
  12-month accumulated rate replacing the fixed 7.0% and 7.0% kept as the fallback (9.2).
- Still to confirm in 9.1: the BCB's terms for republishing FGV series in a public app, and the
  attribution to show ("Fonte: FGV IBRE, via BCB/SGS").
