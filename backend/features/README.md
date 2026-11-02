# Business scenarios (Gherkin)

These feature files are the **executable specification** of the engine. Every number in
them was computed independently of the engine (plain formulas) before the engine was
written, so they work as a regression oracle.

Wording follows the house Gherkin style: business language only, one phrasing per
concept, outcomes in scenario names, twins collapsed into Outlines.

## Vocabulary

| Step | Meaning |
|---|---|
| `Given INCC at X% per year and bank financing at Y% per year over N months` | market assumptions |
| `Given a property "RA" listed at R$ P with N months remaining until delivery` | the apartment under analysis; N is the time **left**, not the project's total duration |
| `Given the developer requires a down payment of X% of the list price` | contract rule |
| `Given the buyer pays R$ X of FGTS upfront` / `in cash upfront` | payments at signing (month 0) |
| `Given the buyer pays the developer R$ X per month` | the monthly installment the buyer chooses |
| `Given the contract has a balloon payment in month N` / `balloon payments in months A and B` | when the uncovered amount is paid — the balloon amount is derived |
| `Given the bank pre-approved a credit of R$ X` | credit approved at signing |
| `When the buyer runs the simulation` | the single action of every scenario |
| `When the buyer re-runs the simulation with ...` | what-if on top of a previous run |
| `When the buyer compares ...` | side-by-side runs |
| `Then the <metric> should be R$ X` | a money figure of the result |

## Model assumptions (decisions taken on the handoff's open questions)

| Topic | Rule |
|---|---|
| Month numbering | Month 0 = signing (upfront). Months 1..N = the N months **remaining** until delivery. Month N = key handover. Bank installments start at N+1. |
| Rates | Annual → monthly by compounding: `(1 + r)^(1/12) − 1`. |
| Down payment | `list_price × pct`. Upfront (FGTS + cash) is deducted at signing; upfront above the down payment reduces the financed balance. Upfront above the list price is rejected; exactly the list price leaves a zero balance. |
| Developer installments | Without a chosen installment: remaining down payment split in N equal nominal installments. With a chosen installment: `missing = remaining − installment × N` is split equally among the balloon months (the balloon is **derived**). Every payment in month k is multiplied by `(1 + incc_pm)^k`. An installment rounded to the cent (≤ half a cent × N) counts as covering the balance. |
| Mortgage balance | `list_price − max(down_payment, upfront)`, corrected by `(1 + incc_pm)^N` at delivery ("hidden INCC debt"). |
| Construction interest | The bank releases the balance evenly over the N months remaining: share k/N after month k. Interest in month k = `corrected_balance_k × (k/N) × bank_pm`. Never amortizes. Physical progress at signing is a [future feature](../../docs/future-features/physical-progress.md). |
| Closing costs | ITBI % + registry/deed % of the list price (defaults 2.0% + 0.5%). |
| Bank financing | SAC and PRICE over `term_months` at `bank_rate_pa`. TR = 0; MIP/DFI insurance and admin fee out of scope. |
| Minimum income | `first_installment / income_commitment_ratio` (default 30%). |
| Credit gap | `max(0, corrected_balance − pre_approved)`; pre-approval defaults to the nominal balance; pro-soluto split linearly, no interest. |

## Tags

Behavioural tags (`@construction`, `@financing`, `@overview`, `@validation`, `@what-if`,
`@more-cash`, `@incc`, `@balloon`, ...) select slices: `behave --tags=@more-cash`.
Allure labels sit on their own tag line (`parentSuite` / `suite` / `subSuite`).
