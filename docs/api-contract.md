# API contract — simulations

*Status: reference for the Connect service, revision 6. The API is no longer REST
([decision](decisions/api-protocol-and-language.md), accepted 2026-11-03): the routes, status codes
and error bodies below are not built. This document stays as the source of the business semantics
(ids, lifetime, comparisons, what-ifs, cash ladders, fields, error cases) from which the RPCs of the
`service Simulations` are derived; revision 7 (task 5.4) restates it as RPCs. Revision 2 replaced the single `POST /api/simulate`
that answered with the whole payload by a simulation resource; revision 3 added
[comparisons](#comparisons); revision 4 added [what-ifs](#what-ifs) — which turn out to be
comparisons with a reference row; revision 5 gave the [cash ladder](#cash-ladders) its own pass
and, reversing revision 4, a route of its own; revision 6 specifies the
[error handling](#errors) — every `400` case with a stable `code`, the API limits, and what a
`500` is and is not. Every endpoint of milestone 5 is now specified.
Decision records: [decisions/what-if-as-comparison.md](decisions/what-if-as-comparison.md),
[decisions/field-specs-from-dtos.md](decisions/field-specs-from-dtos.md) (the shape layer's field
specs and `GET /api/fields`, implemented in `app/controllers/api_requests.py`).*

The Flask controller is a second entry point to the same models and views the CLI uses. This
document fixes what a client may rely on — routes, request shape, response shapes, status codes,
error shape, lifetime — and records **why** ([Reasoning](#reasoning)). The figures themselves are
defined by the business rules in [`backend/features/README.md`](../backend/features/README.md) and
pinned by the behave suite; this document does not restate them.

## The flow

A simulation is a **resource**. The client creates it once and then reads the parts it needs.

```
POST /api/simulations                 body: the flat input (same fields as the CLI flags)
  └─ 201 Created · Location: /api/simulations/{id} · body: {"id", "href"}        (~100 B)

GET  /api/simulations/{id}            the resolved input, the headline summary and the map
  └─ 200                              of sections and fields that can be fetched            (~2.5 KB)

GET  /api/simulations/{id}/{path}     one node of the payload tree, e.g.
                                        mortgage                                             (~100 B)
                                        financing/sac?fields=first_installment,min_income    (~60 B)
                                        timeline/months                                      (~67 KB)
  └─ 200                              the node as JSON

GET  /api/simulations/{id}/result     the whole payload, identical to `python cli.py … --json`  (~180 KB)
GET  /api/fields                      the input fields, types and defaults (the API's `--help`)

GET  /api/comparisons?ids=a,b,c       one summary row per simulation, side by side              (~0.7 KB/row)
POST /api/comparisons                 create several simulations from a base + candidates and
  └─ 201 · Location: /api/comparisons?ids=…   answer with that same comparison

GET  /api/comparisons?ids=v1,v2&relative_to=b   the same rows, each with what it overrides in b
                                                and its delta against b — a what-if             (~1.4 KB/row)
POST /api/simulations/{b}/what-if     create variations of b from a list of overrides and
  └─ 201 · Location: /api/comparisons?ids=…&relative_to=b   answer with that comparison

POST /api/simulations/{b}/cash-ladder the "more cash" sweep: one rung per amount of cash at
  └─ 201 · Location: /api/comparisons?ids=…&relative_to=b   signing — a validated what-if preset
```

Nothing is ever returned that the client did not ask for. A front-end that shows the headline
numbers and the cost breakdown moves ~3 KB over the wire instead of 180 KB; it fetches the
schedules only for the chart that draws them.

```bash
id=$(curl -s -X POST localhost:5000/api/simulations -H 'Content-Type: application/json' \
       -d '{"name":"RA","list_price":440000,"months_remaining":19,"fgts_upfront":13000,
            "developer_installment":2500,"balloon_months":[6,12]}' | jq -r .id)
curl -s localhost:5000/api/simulations/$id/total_cost
curl -s "localhost:5000/api/simulations/$id/financing/sac?fields=first_installment,min_income"
curl -s localhost:5000/api/simulations/$id/result        # == python cli.py --name RA … --json
```

## Routes

| Route | Purpose | Success | Errors |
|---|---|---|---|
| `GET /api/fields` | input fields, types, defaults — for building the form without re-declaring defaults | `200` | — |
| `POST /api/simulations` | validate, run and keep a simulation; return its id | `201` + `Location` | `400` `415` `422` |
| `GET /api/simulations/{id}` | resolved input, headline summary, map of sections and fields | `200` | `404` |
| `GET /api/simulations/{id}/{path}` | one object or array node of the payload; `?fields=` to select keys | `200` | `400` `404` |
| `GET /api/simulations/{id}/result` | the whole payload (CLI parity, tests, export) | `200` | `404` |
| `GET /api/comparisons?ids=…` | summary rows of existing simulations, in the order given; `?fields=` to select columns | `200` | `400` `404` |
| `POST /api/comparisons` | create the simulations of a base + candidates; answer with the comparison | `201` + `Location` | `400` `415` `422` |
| `GET /api/comparisons?ids=…&relative_to={id}` | the same comparison with `overrides` and `delta` per row, measured against one simulation | `200` | `400` `404` |
| `POST /api/simulations/{id}/what-if` | create variations of a stored simulation from overrides; answer with the comparison relative to it | `201` + `Location` | `400` `404` `415` `422` |
| `POST /api/simulations/{id}/cash-ladder` | the same, for increasing amounts of cash at signing (`{"amounts": […]}`) | `201` + `Location` | `400` `404` `415` `422` |

Everything is `application/json`. No authentication. Any other method on these paths is `405`.

## `GET /api/fields`

The input fields a simulation accepts, read from the model DTOs (`input_dto.py`, themselves
generated from `backend/proto/sincero/simulation_input.proto`), so the
front-end form and the CLI `--help` describe the same defaults from the same source.

```json
[
  {"name": "name",              "group": "contract", "type": "string",       "required": false, "default": "CUSTOM", "unit": null},
  {"name": "list_price",        "group": "contract", "type": "number",       "required": true,  "default": null,     "unit": "R$"},
  {"name": "months_remaining",  "group": "contract", "type": "integer",      "required": true,  "default": null,     "unit": "months"},
  {"name": "developer_installment", "group": "contract", "type": "number|null", "required": false, "default": null, "unit": "R$ per month"},
  {"name": "balloon_months",    "group": "contract", "type": "integer[]",    "required": false, "default": [],       "unit": "months"},
  {"name": "incc_rate_pa",      "group": "market",   "type": "number",       "required": false, "default": 7.0,      "unit": "% per year"},
  "…"
]
```

`group` is `contract` | `market` | `bank_credit` (the owning DTO). `type` is one of `string`,
`number`, `integer`, `number|null`, `integer[]`. Fields are listed in DTO order — the same order
as the table below.

## `POST /api/simulations`

### Request

One flat JSON object. Field names are the model's input field names; the grouping into three
DTOs is a model concern and is not visible on the wire.

| Field | Type | Unit | Required | Default | CLI flag |
|---|---|---|---|---|---|
| `name` | string | label | no | `"CUSTOM"` | `--name` |
| `list_price` | number | R$ | **yes** | — | `--price` |
| `months_remaining` | integer | months **remaining** until delivery | **yes** | — | `--months` |
| `down_payment_pct` | number | % of list price | no | `20.0` | `--down-payment-pct` |
| `fgts_upfront` | number | R$ at signing | no | `0.0` | `--fgts` |
| `cash_upfront` | number | R$ at signing | no | `0.0` | `--cash` |
| `developer_installment` | number or `null` | R$ per month | no | `null` = remaining down payment ÷ months | `--installment` |
| `balloon_months` | array of integer | construction months (1..N) | no | `[]` | `--balloon-month` (repeatable) |
| `incc_rate_pa` | number | % per year | no | `7.0` | `--incc` |
| `bank_rate_pa` | number | % per year | no | `10.26` | `--bank-rate` |
| `term_months` | integer | months | no | `360` | `--term` |
| `itbi_pct` | number | % of list price | no | `2.0` | `--itbi` |
| `registry_pct` | number | % of list price | no | `0.5` | `--registry` |
| `income_commitment_ratio` | number | ratio 0–1 | no | `0.30` | `--income-ratio` |
| `pre_approved_credit` | number or `null` | R$ | no | `null` = nominal mortgage balance | `--pre-approved` |
| `pro_soluto_months` | integer | months | no | `12` | `--pro-soluto-months` |

Defaults are **not** repeated in the controller: they come from `field_defaults()`, as they do for
the CLI's `--help`. This table is documentation; the source of truth is
`backend/proto/sincero/simulation_input.proto`, from which the DTOs are generated
([decision](decisions/input-fields-from-proto.md)).

### Shape rules (checked by the controller → `400`)

1. The body must be a JSON **object**. Arrays, scalars, an empty body or malformed JSON are rejected.
2. `list_price` and `months_remaining` must be present.
3. Any key not in the table is rejected — no silent ignoring, no typo tolerance.
4. Types are strict JSON types: a `number` field accepts only a JSON number — not `"440000"`,
   not `true`; an `integer` field accepts only a JSON number with no fractional part (`19` or
   `19.0`, never `19.5`); `balloon_months` must be an array of such integers.
5. Numbers must be finite. `NaN`, `Infinity`, `-Infinity` are rejected even though Python's JSON
   parser would accept them.
6. `null` is accepted only where the table says `or null` (`developer_installment`,
   `pre_approved_credit`) and means "absent". `null` anywhere else is rejected — it is not a way
   to ask for the default; omit the key instead.
7. Numbers and lists are within the [API limits](#api-limits) — upper bounds that keep one
   request bounded in time and size (the model only bounds inputs from below).

Each rule has a stable `code` in the error body (`wrong_type`, `unknown_field`, `missing_field`,
`null_not_allowed`, `not_finite`, `out_of_range`) and `field` names the offending key; see
[Errors](#errors).

### What the server does

Shape rules → `input_from_dict` → `simulate` (so every `SimulationError`, including the
balloon-sizing ones that only surface while simulating, is caught **now**, not on a later GET)
→ store → `201`.

### Response `201 Created`

```http
HTTP/1.1 201 Created
Location: /api/simulations/3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f
Content-Type: application/json

{"id": "3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f", "href": "/api/simulations/3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f"}
```

No figures. The `id` is an opaque string; clients must not parse it. It is **derived from the
resolved input** (a hash of the input with defaults applied), so:

- posting the same input twice yields the same `id` and the same `Location` (the second `POST`
  is also `201`; it refreshes the resource's lifetime);
- the resolved input normalises numbers before hashing, so `2500` and `2500.0` are the same input; two inputs that differ in any field — including `name` — are two resources;
- a client that still has the input can always recreate the exact same URLs (see [Lifetime](#lifetime)).

## `GET /api/simulations/{id}`

The resource itself: what was simulated, the headline figures, and what else can be fetched.
About 2.5 KB.

```json
{
  "id": "3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f",
  "href": "/api/simulations/3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f",
  "created_at": "2026-03-04T15:02:11Z",
  "expires_at": "2026-03-04T16:02:11Z",
  "input": {
    "name": "RA", "list_price": 440000.0, "months_remaining": 19, "down_payment_pct": 20.0,
    "fgts_upfront": 13000.0, "cash_upfront": 0.0, "developer_installment": 2500.0, "balloon_months": [6, 12],
    "incc_rate_pa": 7.0, "bank_rate_pa": 10.26, "term_months": 360, "itbi_pct": 2.0, "registry_pct": 0.5,
    "income_commitment_ratio": 0.3, "pre_approved_credit": null, "pro_soluto_months": 12
  },
  "summary": {
    "name": "RA", "list_price": 440000.0, "months_remaining": 19, "cash_upfront": 0.0,
    "developer_installment": 2500.0, "nominal_balloon": 13750.0, "incc_on_down_payment": 4214.67195925134,
    "hidden_incc_debt": 39802.29732781008, "balance_at_delivery": 391802.2973278101,
    "construction_interest": 30965.098319931145, "closing_costs": 11000.0,
    "sac_first_installment": 4290.330679696464, "sac_last_installment": 1097.2341341463887,
    "price_installment": 3382.5874919155567, "min_income_sac": 14301.102265654881, "min_income_price": 11275.291639718524,
    "credit_gap": 39802.29732781008, "total_cost": 525982.0676069926, "extra_pct": 19.54137900158922,
    "peak_month": 12, "peak_total": 19331.54901372696
  },
  "sections": {
    "input":                 {"href": "…/input",                 "fields": {"name": "string", "list_price": "number", "…": "…"}},
    "rates":                 {"href": "…/rates",                 "fields": {"incc_pm": "number", "bank_pm": "number"}},
    "down_payment":          {"href": "…/down_payment",          "fields": {"required": "number", "upfront": "number", "remaining": "number",
                                                                            "nominal_installment": "number", "missing_amount": "number",
                                                                            "nominal_balloon": "number", "balloons": "array[2]",
                                                                            "total_paid": "number", "incc_correction": "number", "schedule": "array[19]"}},
    "mortgage":              {"href": "…/mortgage",              "fields": {"nominal_balance": "number", "corrected_balance": "number", "hidden_incc_debt": "number"}},
    "construction_interest": {"href": "…/construction_interest", "fields": {"total": "number", "schedule": "array[19]"}},
    "closing_costs":         {"href": "…/closing_costs",         "fields": {"itbi": "number", "registry": "number", "total": "number"}},
    "financing":             {"href": "…/financing",             "fields": {"sac": "object", "price": "object"}},
    "credit_gap":            {"href": "…/credit_gap",            "fields": {"pre_approved": "number", "needed": "number", "gap": "number",
                                                                            "pro_soluto_months": "number", "pro_soluto_installment": "number"}},
    "total_cost":            {"href": "…/total_cost",            "fields": {"list_price": "number", "additional": "number", "total": "number",
                                                                            "extra_pct": "number", "breakdown": "array[5]"}},
    "timeline":              {"href": "…/timeline",              "fields": {"months": "array[380]", "peak_month": "number",
                                                                            "peak_total": "number", "construction_phase_total": "number"}},
    "result":                {"href": "…/result",                "fields": null}
  }
}
```

| Key | Meaning |
|---|---|
| `id`, `href` | as returned by `POST` |
| `created_at`, `expires_at` | RFC 3339 UTC; `expires_at` moves forward on every access (see [Lifetime](#lifetime)) |
| `input` | the **resolved** input: every field of the request table with defaults filled in. `name` is `"CUSTOM"` when omitted; `developer_installment` / `pre_approved_credit` stay `null` when omitted (their resolved values are in `down_payment.nominal_installment` and `credit_gap.pre_approved`); `balloon_months` is echoed as received |
| `summary` | `app/views/json_view.py::summary_to_dict` verbatim — the flat "one row of a comparison" figures; the same row `/api/comparisons` returns per simulation (and a what-if or a cash ladder per rung) |
| `sections` | one entry per top-level payload section plus `result`: its `href` and a `fields` map of *key → kind*, where kind is `number` \| `string` \| `null` \| `object` \| `array[n]` (`n` = number of rows). JSON has no integer type, so the map does not pretend to; which numbers are months is in the [section reference](#section-reference). `result` has no field map (it is the whole tree) |

`sections[*].fields` is computed from the actual payload, so the array sizes are real for this
simulation (`array[19]` for 19 months remaining). It is the runtime answer to "what can I ask
for?"; the [section reference](#section-reference) below is the documented one.

## `GET /api/simulations/{id}/{path}`

**The path is a path into the payload tree.** Segments are the JSON keys of
`simulation_to_dict`, verbatim (`down_payment`, not `down-payment`), separated by `/`. The
response is that node, exactly as it appears in the full payload.

Rules:

1. The node must be an **object or an array**. A path that ends on a scalar (`mortgage/hidden_incc_debt`)
   or does not exist (`financing/foo`, `timeline/months/12`) is `404`. To read scalars, fetch the
   parent and use `fields`.
2. `?fields=a,b,c` keeps only those keys. On an **object** it filters the object; on an **array of
   objects** it filters every row. A name that is not a key of the node (or of its rows) is `400`.
   Order in the response follows the payload, not the query.
3. `result` is a reserved segment: `GET …/{id}/result` returns the whole payload; `…/result/…`
   is `404`.

### Addressable nodes

| Path | Kind | Rows | Size (360-month term, 19 months remaining) |
|---|---|---|---|
| `input` | object | | 0.4 KB |
| `rates` | object | | 0.1 KB |
| `down_payment` | object | | 2.2 KB |
| `down_payment/balloons` | array | `len(balloon_months)` | — |
| `down_payment/schedule` | array | `months_remaining` | 1.9 KB |
| `mortgage` | object | | 0.1 KB |
| `construction_interest` | object | | 2.4 KB |
| `construction_interest/schedule` | array | `months_remaining` | 2.3 KB |
| `closing_costs` | object | | 0.1 KB |
| `financing` | object | | **110 KB** |
| `financing/sac`, `financing/price` | object | | **55 KB** each — use `fields` for the summary |
| `financing/sac/schedule`, `financing/price/schedule` | array | `term_months` | 55 KB each |
| `credit_gap` | object | | 0.2 KB |
| `total_cost` | object | | 0.7 KB |
| `total_cost/breakdown` | array | 5 | 0.6 KB |
| `timeline` | object | | **67 KB** |
| `timeline/months` | array | `1 + months_remaining + term_months` | 67 KB; `?fields=month,total` ≈ 17 KB |
| `result` | object | | 180 KB |

Three nodes carry 97 % of the bytes: the two bank schedules and `timeline/months`. Everything
else together is about 6 KB. Typical front-end usage:

```
GET …/{id}                                             headline, breakdown inputs, sections   2.5 KB
GET …/{id}/total_cost/breakdown                        cost breakdown chart                   0.6 KB
GET …/{id}/financing/sac?fields=first_installment,last_installment,total_interest,total_paid,min_income
GET …/{id}/financing/price?fields=installment,total_interest,total_paid,min_income
GET …/{id}/timeline/months?fields=month,developer_installment,balloon,construction_interest,bank_installment,upfront
                                                       stacked bars (only when that view opens)
```

### Examples

```http
GET /api/simulations/3f9c…/mortgage
200  {"nominal_balance": 352000.0, "corrected_balance": 391802.2973278101, "hidden_incc_debt": 39802.29732781008}

GET /api/simulations/3f9c…/financing/sac?fields=first_installment,min_income
200  {"first_installment": 4290.330679696464, "min_income": 14301.102265654881}

GET /api/simulations/3f9c…/down_payment/balloons
200  [{"month": 6, "nominal": 13750.0}, {"month": 12, "nominal": 13750.0}]

GET /api/simulations/3f9c…/timeline/months?fields=month,total
200  [{"month": 0, "total": 13000.0}, {"month": 1, "total": 2666.3971196593866}, "…"]

GET /api/simulations/3f9c…/mortgage/hidden_incc_debt
404  {"error": "no such node: mortgage/hidden_incc_debt", "code": "not_found", "field": "path"}

GET /api/simulations/3f9c…/mortgage?fields=corrected_balance,foo
400  {"error": "unknown field(s) for mortgage: foo", "code": "invalid_value", "field": "fields"}
```

## `GET /api/simulations/{id}/result`

The dict returned by `simulation_to_dict`, no envelope — byte-for-byte what
`python cli.py … --json` prints for the same input. This is the node the behave suite's HTTP
gateway will read, the one to export, and the one that guarantees the API and the CLI never
disagree. ~180 KB with the default term; serve it gzip-compressed.

## Section reference

Conventions that hold everywhere:

- **Money is a JSON number in R$, not rounded** (e.g. `391802.2973278101`). Rounding and
  `R$ 391.802,30` formatting are the client's job.
- **`month` is an integer** on one axis: `0` = signing, `1..N` = construction (`N = months_remaining`,
  key handover), `N+1..N+term` = bank installments — except inside `financing/*/schedule`, where
  `month` counts from the start of financing (bank month 1 = timeline month `N+1`).
- **Rates in the input are percentages; rates in the result are fractions.** `incc_rate_pa: 7.0`
  in, `rates.incc_pm: 0.00565…` (per month, compounded) out. The one percentage in the result is
  `total_cost.extra_pct`, a headline figure.

### `rates`

| Field | Meaning |
|---|---|
| `incc_pm` | INCC per month, fraction: `(1 + incc_rate_pa/100)^(1/12) − 1` |
| `bank_pm` | bank rate per month, fraction, same conversion |

### `down_payment` — what goes to the developer during construction

| Field | Meaning |
|---|---|
| `required` | `list_price × down_payment_pct / 100` |
| `upfront` | `fgts_upfront + cash_upfront` |
| `remaining` | `max(0, required − upfront)` |
| `nominal_installment` | monthly installment before INCC: the one given, or `remaining / N` |
| `missing_amount` | `remaining − nominal_installment × N`, the part paid as balloons (nominal); `0` without balloons |
| `nominal_balloon` | amount of **one** balloon before INCC (`missing_amount / len(balloons)`); `0` without balloons |
| `balloons[]` | `{month, nominal}` — the **derived** balloons, sorted by month; empty whenever `developer_installment` is `null` |
| `total_paid` | sum of every INCC-corrected payment in `schedule` |
| `incc_correction` | `total_paid − remaining`: what INCC added to the down payment |
| `schedule[]` | one row per construction month `1..N`: `{month, incc_factor, installment, balloon}`; `installment` and `balloon` are INCC-corrected (`nominal × incc_factor`) |

### `mortgage` — the balance handed to the bank

| Field | Meaning |
|---|---|
| `nominal_balance` | `list_price − max(required, upfront)` |
| `corrected_balance` | `nominal_balance × (1 + incc_pm)^N` — what the bank must finance at delivery |
| `hidden_incc_debt` | `corrected_balance − nominal_balance` |

### `construction_interest`

| Field | Meaning |
|---|---|
| `total` | sum of `schedule[].interest` |
| `schedule[]` | one row per construction month `1..N`: `{month, released_share, released_balance, interest}` — `released_share` is the fraction `k/N`, `released_balance` the corrected balance × share, `interest` that balance × `bank_pm` |

### `closing_costs`

`{itbi, registry, total}` — each `list_price × pct / 100`, in R$.

### `financing` — SAC and PRICE side by side

`financing/sac` and `financing/price` share this shape:

| Field | Meaning |
|---|---|
| `first_installment`, `last_installment` | R$ |
| `total_interest`, `total_paid` | over the whole term, R$ |
| `min_income` | `first_installment / income_commitment_ratio` |
| `schedule[]` | one row per bank month `1..term_months`: `{month, installment, interest, amortization, outstanding}`; `outstanding` is the balance after that payment |

plus one system-specific field: `financing/sac` has `amortization` (the constant amortization),
`financing/price` has `installment` (the constant installment).

### `credit_gap` — the "Caixa trigger"

| Field | Meaning |
|---|---|
| `pre_approved` | `pre_approved_credit`, or `mortgage.nominal_balance` when it was `null` |
| `needed` | `mortgage.corrected_balance` |
| `gap` | `max(0, needed − pre_approved)` |
| `pro_soluto_months` | echoed input |
| `pro_soluto_installment` | `gap / pro_soluto_months` (no interest) |

### `total_cost` — the "R$ 440 k → R$ 526 k" view

| Field | Meaning |
|---|---|
| `list_price` | echoed input |
| `additional` | everything paid on top of the list price until delivery |
| `total` | `list_price + additional` |
| `extra_pct` | `additional / list_price × 100` (a percentage) |
| `breakdown[]` | `{component, base_value, additional, final_value}` for `"Down payment"`, `"Mortgage balance"`, `"Construction interest"`, `"Closing costs"` and a closing `"Total"` row; `base_value` adds up to the list price; `final_value = base_value + additional` |

`component` strings are stable identifiers in that order, not translated labels.

### `timeline` — month-by-month cash out

| Field | Meaning |
|---|---|
| `months[]` | one row per month `0..N+term_months`: `{month, developer_installment, balloon, construction_interest, bank_installment, upfront, total}`; `total` is the sum of the other five; `upfront` is non-zero only in month 0; `bank_installment` is the **SAC** installment |
| `peak_month`, `peak_total` | the construction-phase month (`0..N`) with the highest `total`, and that total |
| `construction_phase_total` | sum of `total` over months `0..N` |

### Invariants a client may rely on

- `len(down_payment/schedule) == len(construction_interest/schedule) == months_remaining`
- `len(financing/sac/schedule) == len(financing/price/schedule) == term_months`
- `len(timeline/months) == 1 + months_remaining + term_months`
- `mortgage.corrected_balance == credit_gap.needed`; `credit_gap.gap >= 0`
- `total_cost/breakdown[-1].component == "Total"` and its `final_value == total_cost.total`
- Every number is finite. Every node is the same object it is inside `result`, so any figure is
  covered by a Gherkin scenario.

## Comparisons

A comparison is several simulations **side by side**: the five candidate properties, or — later —
the same property under alternative assumptions. In the model it is nothing more than
`compare(inputs) = [simulate(i) for i in inputs]`, and its view, `comparison_to_dict`, is one
`summary_to_dict` row per result. The behave suite and the text report pin that table
(`features/scenario_comparison.feature`, `comparison_table`).

### The JSON contract

A comparison is an object with the rows, in the order they were asked for:

```json
{
  "href": "/api/comparisons?ids=c47d4fcd08f29ff9832e80af20f56eec,c5becd9763ec702a854421a946cc6062",
  "rows": [
    {
      "id": "c47d4fcd08f29ff9832e80af20f56eec", "href": "/api/simulations/c47d4fcd08f29ff9832e80af20f56eec",
      "name": "SO", "list_price": 300000.0, "months_remaining": 4, "cash_upfront": 0.0,
      "developer_installment": 11750.0, "nominal_balloon": 0.0, "incc_on_down_payment": 668.1291144516872,
      "hidden_incc_debt": 5474.189224721165, "balance_at_delivery": 245474.18922472117,
      "construction_interest": 4987.204927167989, "closing_costs": 7500.0,
      "sac_first_installment": 2688.0022202199652, "sac_last_installment": 687.4453297141625,
      "price_installment": 2119.277828952937, "min_income_sac": 8960.007400733219, "min_income_price": 7064.259429843123,
      "credit_gap": 5474.189224721165, "total_cost": 318629.52326634084, "extra_pct": 6.209841088780281,
      "peak_month": 4, "peak_total": 14024.136653167157
    },
    {
      "id": "c5becd9763ec702a854421a946cc6062", "href": "/api/simulations/c5becd9763ec702a854421a946cc6062",
      "name": "F", "list_price": 396000.0, "months_remaining": 8, "cash_upfront": 0.0,
      "developer_installment": 8275.0, "nominal_balloon": 0.0, "incc_on_down_payment": 1706.781351542173,
      "hidden_incc_debt": 14616.676665438164, "balance_at_delivery": 331416.67666543816,
      "construction_interest": 12029.657737198388, "closing_costs": 9900.0,
      "sac_first_installment": 3629.0934110351054, "sac_last_installment": 928.1254672134545,
      "price_installment": 2861.254037422822, "min_income_sac": 12096.978036783685, "min_income_price": 9537.513458076073,
      "credit_gap": 14616.676665438164, "total_cost": 434253.1157541787, "extra_pct": 9.659877715701699,
      "peak_month": 0, "peak_total": 13000.0
    }
  ]
}
```

A **row** is `summary_to_dict` (the same object as `summary` in `GET /api/simulations/{id}`) plus
two columns, `id` and `href`, that link the row to the simulation it summarises. Rows are flat
because a comparison *is* a table: the Gherkin tables, the text report and the front-end grid all
read it column by column, and `?fields=` selects columns with the same mechanism as everywhere
else. About 0.7 KB per row; five properties are 3.5 KB.

| Column | Unit | Where it comes from in the simulation |
|---|---|---|
| `id`, `href` | | the simulation resource |
| `name`, `list_price`, `months_remaining`, `cash_upfront` | | `input` |
| `developer_installment` | R$/month | `down_payment.nominal_installment` |
| `nominal_balloon` | R$ | `down_payment.nominal_balloon` |
| `incc_on_down_payment` | R$ | `down_payment.incc_correction` |
| `hidden_incc_debt` | R$ | `mortgage.hidden_incc_debt` |
| `balance_at_delivery` | R$ | `mortgage.corrected_balance` |
| `construction_interest` | R$ | `construction_interest.total` |
| `closing_costs` | R$ | `closing_costs.total` |
| `sac_first_installment`, `sac_last_installment` | R$/month | `financing.sac.first_installment`, `.last_installment` |
| `price_installment` | R$/month | `financing.price.installment` |
| `min_income_sac`, `min_income_price` | R$/month | `financing.sac.min_income`, `financing.price.min_income` |
| `credit_gap` | R$ | `credit_gap.gap` |
| `total_cost`, `extra_pct` | R$, % | `total_cost.total`, `total_cost.extra_pct` |
| `peak_month`, `peak_total` | month, R$ | `timeline.peak_month`, `timeline.peak_total` |

Column names are the **summary vocabulary**, not the node vocabulary (`balance_at_delivery` is
`mortgage.corrected_balance`). They are pinned by the Gherkin tables and the cash-ladder view
and are kept as they are; the table above is the bridge. Money is unrounded, as everywhere.

### Which routes fit — the evaluation

The question for comparisons is different from the one for simulations. There, the payload was
180 KB and the answer was "create, then read parts". Here the payload is 0.7 KB per row — a
comparison **is** the small thing a client wants — so bulk is not the issue. The issue is
**identity**: does a comparison row know which simulation it summarises? Five options were
weighed.

| Option | Shape | Verdict |
|---|---|---|
| A. `POST /api/compare` — inputs in, rows out, nothing stored (the ROADMAP's original name) | stateless RPC | **Rejected.** Rows have no `id`; to drill into a row (its timeline, its schedules) the client must re-`POST` the input as a simulation. The table and the detail views would be two unrelated worlds, and the figures would be computed twice. It is also a verb in an API that otherwise has nouns. |
| B. `GET /api/comparisons?ids=a,b,c` — a read over existing simulations | view, no state | **Adopted.** A comparison is a *projection* of simulations that already exist; it needs no store, no lifetime of its own, no new id. Every row links to its simulation, so the table is the entry point to the detail views. Deterministic, cacheable, `fields`-selectable like any node. |
| C. `POST /api/comparisons` → stored comparison → `GET /api/comparisons/{id}` | second resource | **Rejected.** A comparison's entire state is an ordered list of ids, which fits in a query string. A store would add a second lifetime (what happens when one member expires?) for nothing the URL does not already give. |
| D. Batch create — `POST /api/simulations` with an **array** body, then B | two generic steps | **Rejected.** A body that is sometimes an object and sometimes an array is a polymorphic contract; the base + overrides merge — which is how the domain describes candidates (`features/…/scenario_comparison.feature`, `support/world.py`, the CLI reference run) — moves to every client; and a comparison takes two round trips. |
| E. `POST /api/comparisons` with `base` + `candidates` — creates the simulations, answers with B's representation | convenience on top of B | **Adopted.** One request for the CLI-like and test use (the five reference properties), the merge done once on the server where the shape rules already are, and the answer is exactly what `GET` would return — the `Location` *is* the `GET` URL. It creates nothing but simulations, which are content-addressed, so it is as idempotent as `POST /api/simulations`. |

So: **`GET` is the comparison; `POST` is a shortcut that creates its members and then answers
with the `GET`.** A front-end that lets the buyer add candidates one at a time will `POST` each
simulation and `GET` the comparison; a script or a test will `POST` the comparison once.

### `GET /api/comparisons?ids={id},{id},…`

| Parameter | Meaning |
|---|---|
| `ids` | comma-separated simulation ids, **1 to 20**, order preserved; a repeated id repeats the row |
| `fields` | optional; comma-separated row columns to keep (`id` and `href` may be dropped too) |

```http
GET /api/comparisons?ids=c47d…,c5be…,014d…&fields=name,hidden_incc_debt,sac_first_installment,min_income_sac
200  {"href": "/api/comparisons?ids=c47d…,c5be…,014d…",
      "rows": [{"name": "SO", "hidden_incc_debt": 5474.189224721165, "sac_first_installment": 2688.0022202199652, "min_income_sac": 8960.007400733219},
               {"name": "F",  "hidden_incc_debt": 14616.676665438164, "sac_first_installment": 3629.0934110351054, "min_income_sac": 12096.978036783685},
               {"name": "SV", "hidden_incc_debt": 18750.663736791583, "sac_first_installment": 2246.449784988476, "min_income_sac": 7488.165949961587}]}

GET /api/comparisons
400  {"error": "ids is required", "code": "missing_field", "field": "ids"}

GET /api/comparisons?ids=c47d…,deadbeef
404  {"error": "simulation not found: deadbeef", "code": "not_found", "field": "ids"}
```

`href` always carries the full `ids` (never `fields`): it identifies the comparison, not one
projection of it. A comparison lives exactly as long as its least-lived member; reading it
refreshes every member's lifetime.

### `POST /api/comparisons`

```json
{
  "base": {"fgts_upfront": 13000},
  "candidates": [
    {"name": "SO", "list_price": 300000, "months_remaining": 4},
    {"name": "F",  "list_price": 396000, "months_remaining": 8},
    {"name": "SV", "list_price": 233000, "months_remaining": 17},
    {"name": "F4", "list_price": 320400, "months_remaining": 19},
    {"name": "RA", "list_price": 440000, "months_remaining": 19}
  ]
}
```

This is `python cli.py` with no arguments (the reference run).

| Key | Type | Required | Meaning |
|---|---|---|---|
| `base` | object | no (default `{}`) | input fields shared by every candidate |
| `candidates` | array of object, **1 to 20** | yes | per-candidate input fields; each candidate is `{**base, **candidate}` |

Rules:

1. `base` and every candidate may contain only input fields (the `POST /api/simulations` table);
   a key outside it is `400`, naming the offending object (`base` or `candidates[i]`).
2. The **merged** input of each candidate must satisfy every shape rule of
   `POST /api/simulations` — in particular `list_price` and `months_remaining` must be present
   after the merge, in `base` or in the candidate.
3. Every merged input is validated and simulated **before anything is stored**. One bad candidate
   fails the whole request; nothing is created.
4. On success every candidate simulation is stored (same ids as if each had been `POST`ed
   individually) and the response is the comparison:

```http
HTTP/1.1 201 Created
Location: /api/comparisons?ids=c47d4fcd08f29ff9832e80af20f56eec,c5becd9763ec702a854421a946cc6062,…

{"href": "/api/comparisons?ids=c47d…,c5be…,014d…,1e9c…,8489…", "rows": [ … five rows … ]}
```

The body is byte-for-byte what `GET` on the `Location` returns. `201` because simulations were
created (or re-asserted) and the `Location` names where the result of the request lives.

Errors name the candidate. The message stays verbatim (it is the same `422` text as for a single
simulation); the position is a separate key, `index`, and `field` gives the full path:

```http
POST /api/comparisons   {"base": {"fgts_upfront": 13000}, "candidates": [{"name": "SO", "list_price": 300000, "months_remaining": 4},
                                                                          {"name": "F",  "list_price": 396000, "months_remaining": 0}]}
422  {"error": "months remaining until delivery must be at least 1", "code": "invalid_input", "index": 1}

POST /api/comparisons   {"candidates": [{"name": "SO", "list_price": 300000}]}
400  {"error": "candidates[0].months_remaining is required", "code": "missing_field", "field": "candidates[0].months_remaining", "index": 0}

POST /api/comparisons   {"base": {"fgts": 13000}, "candidates": [ … ]}
400  {"error": "unknown simulation input field(s) in base: fgts", "code": "unknown_field", "field": "base.fgts"}

POST /api/comparisons   {"candidates": []}
400  {"error": "candidates must have between 1 and 20 items", "code": "out_of_range", "field": "candidates"}
```

`index` is the zero-based position in `candidates` (or in `variations` / `amounts` for a
what-if / a ladder) and is present whenever the error is about one item; `code` and `field` are
described under [Errors](#errors).

## What-ifs

A what-if is **one simulation under alternative assumptions**: "the same contract with INCC at
4 %", "the same contract with R$ 30,000 more cash at signing", or the cash ladder — the same
contract with increasing cash. In the model, `what_if(base, variations)` runs `base` and
`base.with_overrides(**overrides)` for each variation; its view, `what_if_to_dict`, returns the
base summary and, per variation, the overrides, the summary and a `delta` (summary minus base
summary, numeric columns). `cash_ladder(base, amounts)` is `what_if` with
`{"cash_upfront": a}` per amount. The CLI exposes only the ladder (`--cash-ladder`); the Gherkin
"re-runs the simulation with …" scenarios are a what-if with one variation.

### The JSON contract

Each variation is a full simulation — its resolved input is the base's with a few fields
changed — so it has a content-addressed id like any other. What a what-if adds to a set of
simulations is only a **reference**: which one the others are measured against. The contract is
therefore **the comparison, with a reference row**:

```json
{
  "href": "/api/comparisons?ids=a9279a8269faa5cbc9f867abcabdac53,0e7faba7495f080a3629bda6db89e94e&relative_to=848913523673de9c7c6068ff532397a5",
  "relative_to": {
    "id": "848913523673de9c7c6068ff532397a5", "href": "/api/simulations/848913523673de9c7c6068ff532397a5",
    "name": "RA", "list_price": 440000.0, "months_remaining": 19, "cash_upfront": 0.0,
    "developer_installment": 3947.3684210526317, "hidden_incc_debt": 39802.29732781008, "balance_at_delivery": 391802.2973278101,
    "sac_first_installment": 4290.330679696464, "min_income_sac": 14301.102265654881, "total_cost": 526155.3872753733, "…": "…"
  },
  "rows": [
    {
      "id": "a9279a8269faa5cbc9f867abcabdac53", "href": "/api/simulations/a9279a8269faa5cbc9f867abcabdac53",
      "name": "RA", "list_price": 440000.0, "months_remaining": 19, "cash_upfront": 0.0,
      "developer_installment": 3947.3684210526317, "hidden_incc_debt": 22552.0, "balance_at_delivery": 374552.0,
      "sac_first_installment": 4101.44, "min_income_sac": 13671.45, "total_cost": 506075.28, "…": "…",
      "overrides": {"incc_rate_pa": 4.0},
      "delta": {"list_price": 0.0, "months_remaining": 0, "cash_upfront": 0.0, "developer_installment": 0.0,
                "incc_on_down_payment": -1883.78, "hidden_incc_debt": -17250.3, "balance_at_delivery": -17250.3,
                "construction_interest": -946.03, "sac_first_installment": -188.89, "min_income_sac": -629.65,
                "credit_gap": -17250.3, "total_cost": -20080.11, "extra_pct": -4.56, "…": "…"}
    },
    {
      "id": "0e7faba7495f080a3629bda6db89e94e", "href": "/api/simulations/0e7faba7495f080a3629bda6db89e94e",
      "name": "RA", "cash_upfront": 30000.0, "developer_installment": 2368.42, "hidden_incc_debt": 39802.29732781008, "…": "…",
      "overrides": {"cash_upfront": 30000.0},
      "delta": {"cash_upfront": 30000.0, "developer_installment": -1578.95, "incc_on_down_payment": -1755.2,
                "hidden_incc_debt": 0.0, "sac_first_installment": 0.0, "total_cost": -1755.2, "peak_total": 30000.0, "…": "…"}
    }
  ]
}
```

(Figures abbreviated for reading; the API never rounds.)

| Key | Meaning |
|---|---|
| `relative_to` | the reference simulation as a comparison row (`id`, `href`, the summary columns) — the `base` of `what_if_to_dict`. It is **not** repeated in `rows` unless its id is also in `ids` |
| `rows[].overrides` | the input fields in which this row's **resolved input differs** from the reference's, with this row's values — `{"incc_rate_pa": 4.0}`. Computed by diffing the two resolved inputs, so a no-op override is not listed and `{}` means "identical input" |
| `rows[].delta` | `row[column] − relative_to[column]` for every numeric summary column (all but `name`), in the summary's order — exactly `what_if_to_dict`'s `delta` |

`overrides` and `delta` are the last two columns of a row and are objects; `?fields=` selects
them whole (`fields=name,overrides,delta`). About 1.4 KB per row.

**Labels are not part of the contract.** The model keys variations by a label (`"INCC 4%"`,
`"cash 30,000.00"`) only to carry them through `what_if`; on the wire, `overrides` identifies a
variation unambiguously and machine-readably, and a client renders the label it wants from it
and from `GET /api/fields` (`incc_rate_pa` → "INCC", unit "% per year"). Keeping labels out is
also what lets a what-if be a plain `GET` with nothing stored — see below.

### Which routes fit — the evaluation

| Option | Shape | Verdict |
|---|---|---|
| A. `POST /api/what-if` — base input + labelled variations in, `what_if_to_dict` out, nothing stored (the ROADMAP's name) | stateless RPC | **Rejected**, as for comparisons: rows without ids cannot be drilled into, the base is simulated again although it is on screen, and it would be the third shape for "several summaries side by side". |
| B. A what-if resource — `POST /api/what-ifs` → id → `GET /api/what-ifs/{id}` | second resource | **Rejected.** Its state is a reference id, an ordered list of ids and labels. Without labels it fits in a URL; with labels it would need a store only to remember presentation text. |
| C. `GET /api/comparisons?ids=…&relative_to={id}` — the comparison, measured against one simulation | view, no state | **Adopted.** A what-if *is* a comparison whose rows share almost all of their input with one reference. The reference contributes two derived columns (`overrides`, `delta`), both pure functions of simulations that already exist. No new representation, no new store; the cash ladder, "INCC 4 %" and "R$ 30k more" are all the same `GET`. |
| D. `POST /api/simulations/{id}/what-if` with `variations` — creates the variations of a stored base, answers with C | shortcut on top of C | **Adopted.** This is the front-end's flow: the base is on screen (stored), the buyer tweaks one or two fields, the variations are derived *from that id* — the client does not resend the base. It creates only simulations, so it is idempotent like every other `POST`; the `Location` is C's URL. |
| E. `relative_to` as an index on `POST /api/comparisons` (inline base + candidates + "measure against candidate 0") | one more creation path | **Rejected for now.** It would let a script build a what-if without first storing the base, but it is a second way to produce the same `GET` and needs the awkward `{}` candidate for the base row. Two requests (`POST` the base, `POST` its what-if or cash ladder) are fine; revisit if a script actually wants it. |

So, as with comparisons: **the `GET` is the what-if; the `POST` derives its members from a
stored base and answers with the `GET`.** A what-if and a comparison differ by one query
parameter, and the front-end's "what changes if…" panel and its "candidates" table are the same
component with two extra columns.

### `GET /api/comparisons?ids=…&relative_to={id}`

Everything in [`GET /api/comparisons`](#get-apicomparisonsidsidid) holds, plus:

| Parameter | Meaning |
|---|---|
| `relative_to` | the id of an existing simulation; `404` if unknown or expired. It need not be in `ids`; if it is, that row has `overrides: {}` and all-zero `delta` |

```http
GET /api/comparisons?ids=a927…,0e7f…&relative_to=8489…&fields=overrides,hidden_incc_debt,sac_first_installment,delta
200  {"href": "/api/comparisons?ids=a927…,0e7f…&relative_to=8489…",
      "relative_to": {"hidden_incc_debt": 39802.29732781008, "sac_first_installment": 4290.330679696464},
      "rows": [{"hidden_incc_debt": 22552.0, "sac_first_installment": 4101.44, "overrides": {"incc_rate_pa": 4.0}, "delta": {"…": "…"}},
               {"hidden_incc_debt": 39802.29732781008, "sac_first_installment": 4290.330679696464, "overrides": {"cash_upfront": 30000.0}, "delta": {"…": "…"}}]}

GET /api/comparisons?ids=a927…&relative_to=deadbeef
404  {"error": "simulation not found: deadbeef", "code": "not_found", "field": "relative_to"}
```

`fields` is validated against the row columns (summary + `id`, `href`, `overrides`, `delta`) and
applied to `relative_to` for the columns it has. `href` carries `ids` and `relative_to`, never
`fields`. The what-if lives as long as its shortest-lived member, the reference included.

### `POST /api/simulations/{id}/what-if`

```json
{
  "variations": [
    {"incc_rate_pa": 4.0},
    {"cash_upfront": 30000},
    {"cash_upfront": 30000, "incc_rate_pa": 4.0}
  ]
}
```

| Key | Type | Required | Meaning |
|---|---|---|---|
| `variations` | array of object, **1 to 20** | yes | each item is a set of input-field overrides applied to the stored simulation's resolved input: `{**base_input, **variation}` |

Rules:

1. `{id}` must be an existing simulation — `404` otherwise, before the body is looked at.
2. Each variation may contain only input fields, with the types of the
   [`POST /api/simulations` table](#request) (strict types, finite numbers, `null` only for
   `developer_installment` / `pre_approved_credit` — where it is a meaningful override: "go back
   to automatic sizing"). A key outside the table is `400` with `index`.
3. A variation must not be empty: `{}` is a request for the base itself and is almost certainly
   a client bug — `400`. A variation whose values equal the base's (a cash ladder starting at
   the base's cash) is **valid**; it simply yields the base's own id and `overrides: {}`.
4. Every merged input is validated and simulated **before anything is stored**; one bad
   variation fails the whole request with `index`.
5. On success every variation is stored (same ids as if `POST`ed individually), the base's
   lifetime is refreshed, and the response is the what-if:

```http
HTTP/1.1 201 Created
Location: /api/comparisons?ids=a927…,0e7f…,6c1d…&relative_to=8489…

{"href": "/api/comparisons?ids=a927…,0e7f…,6c1d…&relative_to=8489…", "relative_to": { … }, "rows": [ … three rows … ]}
```

The body is byte-for-byte what `GET` on the `Location` returns. Rows are in the order of
`variations`; two variations with the same effective input produce the same id twice.

```http
POST /api/simulations/8489…/what-if   {"variations": [{"incc_rate_pa": 4.0}, {"incc_rate_pa": -150}]}
422  {"error": "INCC rate must be greater than -100% per year", "code": "invalid_input", "index": 1}

POST /api/simulations/8489…/what-if   {"variations": [{"incc": 4.0}]}
400  {"error": "unknown simulation input field(s) in variations[0]: incc", "code": "unknown_field", "field": "variations[0].incc", "index": 0}

POST /api/simulations/8489…/what-if   {"variations": [{}]}
400  {"error": "variations[0] is empty", "code": "invalid_value", "field": "variations[0]", "index": 0}

POST /api/simulations/deadbeef/what-if
404  {"error": "simulation not found: deadbeef", "code": "not_found"}
```

## Cash ladders

The cash ladder is the product's headline "what if I put more cash on the table" view
(README: *what changes when you put more cash on the table*). The model has it as
`cash_ladder(base, amounts)` = `what_if(base, {"cash …": {"cash_upfront": a} for a in amounts})`,
the CLI as `--cash-ladder 0,30000,75000,100000`, the Gherkin suite as "the buyer compares paying
the following cash upfront" with a `cash` column, and `tests/test_models.py` pins that it is
monotonic. The domain rule it illustrates: cash at signing first reduces the developer
installment; only once the down payment is fully covered does it reduce the financed balance
(the RA example: R$ 75,000 zeroes the installment, R$ 100,000 is the first rung that lowers the
hidden INCC debt).

### The JSON contract

A ladder is a what-if whose variations differ in **one field**, `cash_upfront`, and are
**ordered**. Its representation is therefore the what-if's — the comparison with a reference —
with nothing added: rows are the rungs in ascending amount, `relative_to` is the base, each
row's `overrides` is `{"cash_upfront": a}` (or `{}` for the rung equal to the base) and its
`delta` says what that amount buys. The `cash` column of the Gherkin table is the row's
`cash_upfront`.

```json
{
  "href": "/api/comparisons?ids=0686cdb7…,4387d4f1…,bed31964…,979fb5f3…&relative_to=0686cdb7…",
  "relative_to": {"id": "0686cdb7…", "href": "/api/simulations/0686cdb7…", "name": "RA", "cash_upfront": 0.0,
                  "developer_installment": 3947.37, "hidden_incc_debt": 39802.30, "sac_first_installment": 4290.33, "min_income_sac": 14301.10, "…": "…"},
  "rows": [
    {"id": "0686cdb7…", "cash_upfront": 0.0,      "developer_installment": 3947.37, "hidden_incc_debt": 39802.30, "balance_at_delivery": 391802.30, "sac_first_installment": 4290.33, "min_income_sac": 14301.10, "…": "…",
     "overrides": {},                         "delta": {"total_cost": 0.0,      "peak_total": 0.0,      "…": "…"}},
    {"id": "4387d4f1…", "cash_upfront": 30000.0,  "developer_installment": 2368.42, "hidden_incc_debt": 39802.30, "balance_at_delivery": 391802.30, "sac_first_installment": 4290.33, "min_income_sac": 14301.10, "…": "…",
     "overrides": {"cash_upfront": 30000.0},  "delta": {"total_cost": -1755.20, "peak_total": 30000.0,  "…": "…"}},
    {"id": "bed31964…", "cash_upfront": 75000.0,  "developer_installment": 0.0,     "hidden_incc_debt": 39802.30, "balance_at_delivery": 391802.30, "sac_first_installment": 4290.33, "min_income_sac": 14301.10, "…": "…",
     "overrides": {"cash_upfront": 75000.0},  "delta": {"total_cost": -4387.99, "peak_total": 75000.0,  "…": "…"}},
    {"id": "979fb5f3…", "cash_upfront": 100000.0, "developer_installment": 0.0,     "hidden_incc_debt": 36975.43, "balance_at_delivery": 363975.43, "sac_first_installment": 3985.62, "min_income_sac": 13285.40, "…": "…",
     "overrides": {"cash_upfront": 100000.0}, "delta": {"total_cost": -9414.09, "peak_total": 100000.0, "…": "…"}}
  ]
}
```

(Figures rounded for reading; the API never rounds. These are the rows of the Gherkin scenario
*A cash ladder shows what each extra real at signing buys*.)

Nothing ladder-specific is needed in the rows: the x-axis is `cash_upfront`, the y-axes are the
summary columns, the chart is `rows[*].cash_upfront` against `rows[*].developer_installment`,
`hidden_incc_debt`, `sac_first_installment`… and `delta` is the "what each extra real buys".
The first rung is the base itself whenever its amount equals the base's cash — same id,
`overrides: {}`, zero `delta` — which is exactly what the CLI and the Gherkin table show as
the `0.00` row.

### Which routes fit — the evaluation

Revision 4 concluded "no separate route: a ladder is a what-if the client builds in one line".
That was true of the *representation* and still is. Taking the ladder on its own, the question
is whether its **request** deserves a contract. What changed in the evaluation is noticing that a
ladder has shape rules a generic what-if cannot express (ascending, distinct amounts) and that
it is the one sweep the product names, in the CLI, the Gherkin suite and the front-end
milestone alike.

| Option | Shape | Verdict |
|---|---|---|
| A. `POST /api/cash-ladder` — base input + amounts in, `what_if_to_dict` out, nothing stored (the ROADMAP's name) | stateless RPC | **Rejected**, for the reasons that retired `/api/simulate`, `/api/compare` and `/api/what-if`: no ids, the base simulated again, a private response shape with labels. |
| B. Client-built what-if — `POST /api/simulations/{id}/what-if` with `[{"cash_upfront": a}, …]` (revision 4) | no route | **Superseded.** It works and stays valid. But the ladder's own mistakes — amounts out of order, repeated, negative — pass as legitimate variations and come back as a confusing table instead of a `400`; and the CLI flag, the Gherkin step and the front-end view all name a thing the API would not. |
| C. `GET /api/simulations/{id}/cash-ladder?amounts=0,30000,75000,100000` | a read | **Rejected, narrowly.** The ladder is the one what-if whose parameters fit a query string, so a bookmarkable, browser-cacheable URL is tempting. But the rungs must exist as simulations for their `href`s to work, so the `GET` would create them — a side effect the document's one rule ("`POST` creates, `GET` reads") exists to forbid. And the gain is small: the `POST`'s `Location` is already a bookmarkable `GET`. |
| D. `POST /api/simulations/{id}/cash-ladder` with `{"amounts": […]}` — a validated preset that creates the rungs and answers with the what-if `GET` | shortcut on top of the what-if | **Adopted.** Same mechanics as `…/what-if` (derive from a stored base, store, answer with `GET /api/comparisons?…&relative_to`), plus the ladder's own shape rules and a 1:1 mapping to `--cash-ladder`. Costs one route and a three-line body; adds no representation, no labels, no state. |
| E. A generic sweep — `POST /api/simulations/{id}/sweep` with `{"field": "incc_rate_pa", "values": […]}` | generalisation | **Deferred.** An INCC sweep is the obvious second use (the "lower INCC" scenario; live INCC is milestone 9). Until a second sweep exists, a generic route would be speculation; `cash-ladder` can become an alias of it without changing its contract. |

So: **one more `POST` preset, no new `GET`, no new representation.** A ladder's URL after
creation is a what-if's URL.

### `POST /api/simulations/{id}/cash-ladder`

```json
{"amounts": [0, 30000, 75000, 100000]}
```

| Key | Type | Required | Meaning |
|---|---|---|---|
| `amounts` | array of number, **1 to 20** | yes | cash at signing for each rung, **absolute** (`cash_upfront` is set to the amount, not added to the base's), in R$ |

Rules:

1. `{id}` must be an existing simulation — `404` otherwise, before the body is looked at.
2. `amounts` must be finite numbers, **≥ 0**, **strictly increasing**. Anything else is `400`
   with `index` pointing at the first offending amount (the one that is negative, or not greater
   than its predecessor). A ladder is ascending by definition; an unsorted or repeated list is a
   client bug, not a ladder to be fixed up silently.
3. Each rung is `base.with_overrides(cash_upfront=a)`, validated and simulated **before
   anything is stored**; one bad rung fails the whole ladder with `index` — in particular a rung
   whose FGTS + cash exceeds the list price
   ([decision](decisions/reject-upfront-above-list-price.md)).
4. On success the rungs are stored (same ids as `…/what-if` would give), the base's lifetime is
   refreshed, and the response is the what-if:

```http
HTTP/1.1 201 Created
Location: /api/comparisons?ids=0686cdb7…,4387d4f1…,bed31964…,979fb5f3…&relative_to=0686cdb7…

{"href": "/api/comparisons?ids=…&relative_to=0686cdb7…", "relative_to": { … }, "rows": [ … four rows … ]}
```

`python cli.py --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000` is:

```http
POST /api/simulations                     {"list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000}
201  {"id": "0686cdb7…", …}
POST /api/simulations/0686cdb7…/cash-ladder   {"amounts": [0, 30000, 75000, 100000]}
201  Location: /api/comparisons?ids=0686cdb7…,4387d4f1…,bed31964…,979fb5f3…&relative_to=0686cdb7…
```

and the CLI's `--json` for the same ladder (`what_if_to_dict`) carries the same `summary` and
`delta` figures per rung, under its own labels.

```http
POST /api/simulations/0686cdb7…/cash-ladder   {"amounts": [0, 30000, 30000]}
400  {"error": "amounts must be strictly increasing: amounts[2] = 30000 is not greater than amounts[1]", "code": "invalid_value", "field": "amounts[2]", "index": 2}

POST /api/simulations/0686cdb7…/cash-ladder   {"amounts": [0, -1]}
400  {"error": "amounts must not be negative: amounts[1] = -1", "code": "out_of_range", "field": "amounts[1]", "index": 1}

POST /api/simulations/0686cdb7…/cash-ladder   {"amounts": [0, 500000]}
422  {"error": "upfront payments of R$ 513,000.00 exceed the list price of R$ 440,000.00", "code": "invalid_input", "index": 1}

POST /api/simulations/0686cdb7…/cash-ladder   {"amounts": []}
400  {"error": "amounts must have between 1 and 20 items", "code": "out_of_range", "field": "amounts"}
```

## Errors

### The error body

Every non-2xx response from the backend — including the ones Flask would normally answer with an
HTML page (unknown route, wrong method, wrong content type, malformed JSON, body too large) — is
`application/json` with this body:

```json
{"error": "candidates[1].months_remaining must be an integer, got \"19\"",
 "code": "wrong_type",
 "field": "candidates[1].months_remaining",
 "index": 1}
```

| Key | Always | Meaning |
|---|---|---|
| `error` | yes | one human-readable sentence. For `422` it is the model's message, verbatim and contractual — the text the CLI prints after `error:`, meant for the buyer. For every other status it is for the developer and its wording is **not** contractual |
| `code` | yes | a stable `snake_case` identifier of the cause — the thing a client branches on within a status. The full list is below; new codes may be added, existing ones are never renamed |
| `field` | when the error is about one key or parameter | its path from the body root (`list_price`, `balloon_months[1]`, `base.fgts`, `candidates[1].months_remaining`, `variations[0]`, `amounts[2]`) or, for a `GET`, the query parameter name (`ids`, `fields`, `relative_to`) |
| `index` | when the error is about one item of `candidates`, `variations` or `amounts` | that item's zero-based position — the row to highlight, without parsing `field` |
| `request_id` | on `500` only | the value of the `X-Request-Id` response header, to quote when reporting the bug |

Nothing else is ever in an error body: no stack, no exception class, no internal path.

Every response, success or error, carries an `X-Request-Id` header: the client's own if it sent
one (up to 64 printable ASCII characters), otherwise a server-generated UUID.

### Status codes and codes

| Status | `code` | When | Decided by |
|---|---|---|---|
| `400` | `malformed_json` | the body is not valid JSON (also: empty body on a `POST`) | controller |
| `400` | `wrong_type` | a value has the wrong JSON type: `"440000"` or `true` for a number, `19.5` for an integer, an object where an array is expected, a body that is not an object | controller |
| `400` | `unknown_field` | a key that is not an input field (in the body, `base`, a candidate or a variation); a query parameter the route does not define | controller |
| `400` | `missing_field` | `list_price` or `months_remaining` absent after the merge; `candidates`, `variations` or `amounts` absent; `ids` absent | controller |
| `400` | `null_not_allowed` | `null` for a field that is not `developer_installment` / `pre_approved_credit` | controller |
| `400` | `not_finite` | `NaN`, `Infinity`, `-Infinity` anywhere a number is expected | controller |
| `400` | `out_of_range` | a number outside the [API limits](#api-limits); a list with fewer or more items than allowed (`balloon_months`, `candidates`, `variations`, `amounts`, `ids`); a negative ladder amount | controller |
| `400` | `invalid_value` | a value of the right type that cannot be used: an empty variation `{}`; a non-ascending ladder; an unknown or empty name in `fields`; an empty `ids`; a non-object candidate/variation | controller |
| `404` | `not_found` | no such route; an unknown or expired simulation id (in the path, in `ids`, in `relative_to`); a `path` that is not an object/array node of the payload | controller |
| `405` | `method_not_allowed` | the route exists, the method does not (`PUT /api/simulations/{id}`). `Allow` header set | Flask, body by the controller |
| `413` | `payload_too_large` | the body exceeds **64 KB** (the largest legitimate body — 20 candidates — is about 10 KB) | Flask, body by the controller |
| `415` | `unsupported_media_type` | a `POST` whose `Content-Type` is not `application/json` (a `charset` parameter is fine) | Flask, body by the controller |
| `422` | `invalid_input` | the input — or one candidate's / variation's / rung's merged input, `index` says which — is well-formed but describes an impossible contract: any `SimulationError`. The message is the contract; see [the `422` rules](#the-422-rules) | the model |
| `500` | `internal_error` | a bug. Constant message `"internal error"`, plus `request_id` | the controller's last-resort handler |

The `code` of a `422` is deliberately a single value: the model raises one exception type and its
messages are the contract. Per-rule codes would require the model to carry them; that is an
[open question](#open-questions).

### `400` — order of checks

Several rules can be broken at once; the client always sees the **first** one in this order, so
the same bad request gets the same answer every time. The order is "outermost first", which is
also "cheapest first":

1. The route and the method (`404`, `405`).
2. For `/api/simulations/{id}/…`: the simulation exists (`404`) — before the body is read.
3. `Content-Type` (`415`), then body size (`413`), then JSON syntax (`400 malformed_json`).
4. The body is an object (`wrong_type`, `field: "body"`); on the comparison / what-if / ladder
   routes, the wrapper keys (`base`, `candidates`, `variations`, `amounts`) exist and have the
   right type and size (`missing_field`, `wrong_type`, `out_of_range`).
5. Unknown keys (`unknown_field`; one error naming the first unknown key in document order,
   the message listing all of them).
6. Required keys (`missing_field`).
7. Field by field, in the order of the [request table](#request) (DTO order): `null`
   (`null_not_allowed`), type (`wrong_type`), finiteness (`not_finite`), limits (`out_of_range`);
   for `balloon_months`, item by item.
8. On multi-item routes, steps 4–7 run per item, in item order; the first failing item ends the
   request with its `index`. Nothing is stored when any item fails.
9. Only then the model (`422`), also item by item, in item order.

For `GET`s: unknown query parameters first (`unknown_field`), then `ids` / `relative_to`
(`missing_field`, `invalid_value`, `out_of_range`, then `404` for each id in order), then `fields`
(`invalid_value`), then the path walk (`404`).

### API limits

The model bounds its inputs from below (business rules, `422`). The API also bounds them from
above, as a **protective** measure: simulation time and payload size grow linearly with the month
counts (`months_remaining = term_months = 5000` takes 2.4 s and 4 MB *per simulation*), and a
magnitude near the float ceiling would put `Infinity` into a payload that promises finite
numbers. These are `400 out_of_range`, decided by the controller, and are not business rules: a
financing term of 600 months does not exist in Brazil, but rejecting it for that reason would be
the model's job (`422`), and it is listed as an open question.

| Field | Limit |
|---|---|
| `months_remaining`, `term_months`, `pro_soluto_months` | ≤ 600 |
| `balloon_months` | ≤ 60 items (each within `1..months_remaining` is the model's rule) |
| `list_price`, `fgts_upfront`, `cash_upfront`, `developer_installment`, `pre_approved_credit`, each ladder amount | ≤ 10¹² (one trillion reais) |
| `down_payment_pct`, `itbi_pct`, `registry_pct`, `incc_rate_pa`, `bank_rate_pa` | ≤ 1000 (%) |
| `candidates`, `variations`, `amounts`, `ids` | 1 to 20 items |
| `fields` | ≤ 50 names |
| request body | ≤ 64 KB (`413`) |
| `X-Request-Id` from the client | ≤ 64 printable ASCII characters; longer or non-ASCII values are replaced by a server id, not rejected |

The worst legitimate request under these limits — a comparison of 20 candidates at 600 months —
takes about four seconds and is served whole; there is no timeout of the API's own.

### `400` examples

```http
POST /api/simulations                    (body: "{")
400  {"error": "request body is not valid JSON", "code": "malformed_json"}

POST /api/simulations                    [1, 2]
400  {"error": "request body must be a JSON object", "code": "wrong_type", "field": "body"}

POST /api/simulations                    {"list_price": "440000", "months_remaining": 19}
400  {"error": "list_price must be a number, got a string", "code": "wrong_type", "field": "list_price"}

POST /api/simulations                    {"list_price": 440000, "months_remaining": 19.5}
400  {"error": "months_remaining must be an integer, got 19.5", "code": "wrong_type", "field": "months_remaining"}

POST /api/simulations                    {"list_price": 440000, "months_remaining": 19, "fgts_upfrnt": 13000, "foo": 1}
400  {"error": "unknown simulation input field(s): fgts_upfrnt, foo", "code": "unknown_field", "field": "fgts_upfrnt"}

POST /api/simulations                    {"list_price": 440000}
400  {"error": "months_remaining is required", "code": "missing_field", "field": "months_remaining"}

POST /api/simulations                    {"list_price": 440000, "months_remaining": 19, "itbi_pct": null}
400  {"error": "itbi_pct must not be null; omit it to use the default", "code": "null_not_allowed", "field": "itbi_pct"}

POST /api/simulations                    {"list_price": NaN, "months_remaining": 19}
400  {"error": "list_price must be a finite number", "code": "not_finite", "field": "list_price"}

POST /api/simulations                    {"list_price": 440000, "months_remaining": 5000}
400  {"error": "months_remaining must be at most 600", "code": "out_of_range", "field": "months_remaining"}

POST /api/comparisons                    {"candidates": [{"name": "SO", "list_price": 300000}]}
400  {"error": "candidates[0].months_remaining is required", "code": "missing_field", "field": "candidates[0].months_remaining", "index": 0}

POST /api/simulations/8489…/what-if      {"variations": [{"incc_rate_pa": 4.0}, {}]}
400  {"error": "variations[1] is empty", "code": "invalid_value", "field": "variations[1]", "index": 1}

POST /api/simulations/8489…/cash-ladder  {"amounts": [0, 30000, 30000]}
400  {"error": "amounts must be strictly increasing: amounts[2] = 30000 is not greater than amounts[1]", "code": "invalid_value", "field": "amounts[2]", "index": 2}

GET  /api/simulations/8489…/mortgage?field=corrected_balance
400  {"error": "unknown query parameter: field (did you mean fields?)", "code": "unknown_field", "field": "field"}

GET  /api/comparisons?ids=
400  {"error": "ids must contain at least one simulation id", "code": "invalid_value", "field": "ids"}
```

### `500` — what it is and what it is not

A `500` means **the backend has a bug**. It is never the answer to a bad request: every way a
request can be wrong is a `4xx` above, and the shape layer exists precisely so that no
`TypeError` from the model ever surfaces. Concretely, a `500` is raised by the last-resort
handler when any of these happens — and each is a defect to fix, not a case to document for
clients:

- an exception other than `SimulationError` escapes the model or the views (a `TypeError` here
  means the shape layer let a value through);
- a `SimulationError` is raised while serving a **`GET`** — stored inputs were validated and
  simulated at creation, so this means the store holds something it should not;
- the payload contains a non-finite number. The JSON serializer runs with `allow_nan=False`
  (Flask's default would emit the `NaN` literal, which is not JSON); a `ValueError` there is a
  bug in the model's arithmetic, and a `500` is the honest answer — a client must never receive
  invalid JSON or a number it cannot parse;
- the path walk, the `fields` projection or the store raise anything.

What the client gets:

```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
X-Request-Id: 7c1e4b2a-5d3f-4e8a-9b0c-1f2a3b4c5d6e

{"error": "internal error", "code": "internal_error", "request_id": "7c1e4b2a-5d3f-4e8a-9b0c-1f2a3b4c5d6e"}
```

The body is constant apart from `request_id`. The exception's type, message and traceback never
reach the client, whatever Flask's `debug` setting is — the last-resort handler is installed
for `Exception`, not only for `HTTPException`, and the API is never deployed with
`debug=True`.

What the server does: one log record at level `ERROR` with the request id, method, path, the
request body (truncated to 4 KB; inputs are numbers and a label, not personal data), and the
full traceback. Nothing else — no retry, no partial store: a `500` on a `POST` stores nothing,
so a client may simply retry once the bug is fixed, and the content-addressed ids guarantee the
retry is idempotent.

What a `500` is **not**: a missing dependency (there is none), a timeout (there is none), an
expired simulation (`404`), a store at capacity (it evicts, never fails), an overloaded server
(the limits above keep a single request bounded; overload shows as latency, not as errors).

### Flask's own errors

Flask answers unknown routes, wrong methods, wrong content types, oversize and malformed bodies
with HTML pages. The controller registers one handler for `werkzeug.exceptions.HTTPException`
that rewrites every one of them into the body above with the matching `code`
(`not_found`, `method_not_allowed`, `unsupported_media_type`, `payload_too_large`,
`malformed_json`), keeping Flask's status and headers (`Allow` on `405`). So even `GET /` on the
backend is `404 {"error": "not found", "code": "not_found"}`. Responses to CORS preflight
(`OPTIONS`, handled by flask-cors) are outside this contract.

### The `422` rules

Validation stops at the **first** broken rule, in this order. Messages are verbatim.

Contract (`PropertyValidator` → `UpfrontPaymentsValidator` → `DeveloperPlanValidator`):

- `list price must be greater than zero`
- `months remaining until delivery must be at least 1`
- `down payment percentage must be between 0 and 100`
- `upfront payments must not be negative`
- `upfront payments of R$ 500,000.00 exceed the list price of R$ 440,000.00` (figures vary; see [decision](decisions/reject-upfront-above-list-price.md))
- `the monthly developer installment must not be negative`
- `balloon month 25 is after delivery (month 19)` · `balloon month 0 must be at least 1` · `balloon months must not repeat`

Market (`MarketRatesValidator` → `FinancingValidator` → `ClosingCostsValidator`):

- `INCC rate must be greater than -100% per year` (negative INCC, i.e. deflation, is valid)
- `bank interest rate must not be negative`
- `financing term must be at least 1 month`
- `income commitment ratio must be between 0 and 1`
- `closing cost percentages must not be negative`

Bank credit (`BankCreditValidator`):

- `pre-approved credit must not be negative`
- `pro-soluto term must be at least 1 month`

Sizing the developer plan (`DownPaymentPlan`, raised while simulating — still a `422` on `POST`):

- `a monthly developer installment is required to size the balloon payments`
- `monthly installments of R$ 1,900,000.00 exceed the down payment balance of R$ 88,000.00`
- `monthly installments of R$ 1,900.00 do not cover the down payment balance of R$ 88,000.00; R$ 86,100.00 is missing — add balloon months or raise the installment`

## Lifetime

- A simulation lives in the **backend process's memory**. It is kept for a **TTL after its last
  access** (default 1 hour, `SINCERO_SIMULATION_TTL_SECONDS`), bounded by a maximum number of
  simulations (default 1000, `SINCERO_SIMULATION_CAPACITY`, least-recently-used evicted first).
  `expires_at` on the resource reports the current deadline.
- After the TTL, after eviction, or after a **restart**, every URL of that id answers `404`.
- **Recovery is a re-`POST` of the same input**: because the id is derived from the input, the
  client gets the same id back and every URL it holds is valid again. The front-end keeps the
  form state anyway, so this is one request, not a rebuild.
- What is stored is the **resolved input** (~400 bytes). The result is recomputed on demand
  (~3 ms to simulate, ~8 ms to serialise) and may be cached; whether it is cached is invisible
  to clients.
- Consequence for deployment (milestone 7): the backend must run as **one process** (threads are
  fine). Several worker processes would each hold their own store, and a `GET` would land on a
  worker that never saw the `POST`. A shared store is the alternative if that ever becomes a
  constraint — see [open questions](#open-questions).

## How it maps onto the code

```
POST /api/simulations ─► api_controller      shape rules ──────────────────────────── 400
                           │ input_from_dict          (app/views/json_view.py)
                           │ simulate                 (app/models) — SimulationError ── 422
                           │ store.put(resolved input) → id
                           └──────────────────────────────────────────────────────── 201

GET  /api/simulations/{id}[/path] ─► api_controller
                           │ store.get(id) ───────────────────────────────────────── 404
                           │ simulate + simulation_to_dict   (cached or recomputed)
                           │ walk path; apply ?fields ─────────────────────────────── 400/404
                           └──────────────────────────────────────────────────────── 200

GET  /api/fields ─► api_controller ─► dataclasses.fields(ContractData | MarketData | BankCreditData)

GET  /api/comparisons?ids ─► api_controller
                           │ store.get(each id) ─────────────────────────────────── 404
                           │ compare(inputs) + comparison_to_dict   (app/models, app/views)
                           │ add id/href per row; apply ?fields ──────────────────── 400
                           └──────────────────────────────────────────────────────── 200

POST /api/comparisons ─► api_controller
                           │ shape rules on base/candidates; merge ───────────────── 400
                           │ input_from_dict + simulate, every candidate ─────────── 422
                           │ store.put(each)
                           └── the GET above ──────────────────────────────────────── 201

GET  …&relative_to={id} ─► as GET /api/comparisons, plus
                           │ store.get(relative_to) ─────────────────────────────── 404
                           │ overrides = diff(row.input, ref.input); delta = summary − ref summary
                           └──────────────────────────────────────────────────────── 200

POST /api/simulations/{id}/what-if ─► api_controller
                           │ store.get(id) ──────────────────────────────────────── 404
                           │ shape rules on variations ───────────────────────────── 400
                           │ base.with_overrides(**v) + simulate, every variation ── 422
                           │ store.put(each)
                           └── the GET above, relative_to = id ───────────────────── 201

POST /api/simulations/{id}/cash-ladder ─► api_controller
                           │ store.get(id) ──────────────────────────────────────── 404
                           │ ladder rules on amounts (finite, ≥ 0, ascending) ────── 400
                           └── the what-if above with variations = [{cash_upfront: a} …]
```

Nothing in `app/models` changes. In `app/views`, `summary_to_dict`, `simulation_to_dict`,
`input_from_dict` and `error_to_dict` are used as they are; three small presenters are new: the
resource representation (`simulation_resource_to_dict`: id, input, summary, sections), the
field list (`fields_to_dict`) and the comparison (`comparison_resource_to_dict`: href + rows with
id/href — a thin wrapper over `comparison_to_dict`; with a reference it adds `overrides` and
`delta`, the latter with the same arithmetic as `what_if_to_dict`). `what_if`, `cash_ladder` and
`what_if_to_dict` stay as they are for the CLI; the API reaches the same results through
`with_overrides` + `simulate`, which is all they do. The controller adds the shape rules, the store, the path walk and
the status mapping.

## Reasoning

### 1. Create, then read parts — instead of one `POST` that returns everything

**Why.** 97 % of the 180 KB payload is three arrays a screen needs only when it draws the
corresponding chart; the headline figures are 690 bytes. Returning everything on every
simulation is the CLI's shape (one shot, one file) carried into a medium where it does not fit.
A resource the client reads selectively sends what is looked at, and makes it natural to add
reads later (a month range of the timeline, a comparison of stored ids) without touching the
create.

**Cost, stated plainly.** The API is now **stateful**: a store, a lifetime, a `404` after a
restart, a single-process constraint. Decisions 2–4 are about keeping that cost small.

### 2. The id is a hash of the resolved input

**Why.** A simulation is a pure function of its input. Deriving the id from the input makes the
`POST` idempotent (no duplicate resources from a double-click or a retry), makes `404`-after-restart
recoverable by re-posting the same form state, and means the same input always has the same
URLs — which the behave HTTP gateway and the front-end tests can rely on. A random UUID would
give none of this for no benefit.

**Rejected.** Encoding the *whole input* into the id (a base64 token) would make the server fully
stateless — no store, no TTL, no worker constraint — but produces 400-character URLs, makes the
`POST` do nothing but validate, and forecloses a list endpoint. Kept as the fallback if the
single-process constraint ever bites (see open questions).

### 3. Store the input, recompute the result

**Why.** The input is 376 bytes; the result is 180 KB and costs 3 ms to rebuild. Storing inputs
makes capacity a non-issue (1000 simulations ≈ 400 KB) and the store trivial; a result cache is
an optimisation the contract never mentions. It also rules out a whole class of staleness bugs:
there is exactly one source of truth for a figure — the model, run now.

### 4. `POST` returns only `{id, href}`

**Why.** Asked for, and right: the create should not pre-empt what the client will read. The
headline figures are one 2.5 KB `GET` away, and that `GET` is the one the front-end needs
anyway to learn the sections. `201` is returned even when the id already existed — the
distinction (`200` vs `201`) would cost a branch on both sides and tell the client nothing it
can act on.

### 5. The URL path is the JSON path, keys verbatim

**Why.** One rule instead of a routing table: `…/financing/sac/schedule` *is*
`result["financing"]["sac"]["schedule"]`. There is nothing to map, nothing to keep in sync, and
the same names work in `sections`, in `fields`, and in the CLI's `--json`. Using `snake_case` in
paths (rather than `kebab-case` like the action routes `…/what-if` and `…/cash-ladder`) is the
price of that identity; action routes are verbs and can stay hyphenated.

**Rejected.** A hand-written route per section — more code, and every new payload key would need
a route; a GraphQL-style field selector — `?fields=` on a node covers the real need (summary
without the schedule, two columns of the timeline) with a dozen lines.

### 6. Only object/array nodes are addressable; `?fields=` reads scalars

**Why.** A JSON body that is a bare number is legal but awkward for every client library, and
one request per scalar is the wrong granularity anyway. `fields` on the parent gives any subset
of scalars in one round trip, and the same mechanism projects columns out of a 380-row array,
which is what a chart actually wants.

### 7. `GET /api/fields` — the API's `--help`

**Why.** `test_cli_defaults_are_the_model_defaults` exists so that the CLI never re-declares the
model's defaults. The front-end form has the same temptation. Serving the field list from the
DTOs gives the form one source of truth for names, types and defaults; `group` lets it lay the
form out as contract / market / bank without knowing the DTOs.

### 8. Keep `/result`

**Why.** It is the CLI's `--json` and the payload the behave suite asserts against. Keeping it
addressable means the API can be tested for *equality* with the CLI, an export is one call, and
anyone who wants the old one-shot behaviour still has it — they just have to ask.

### 9. Two validation layers, two status codes (`400` shape, `422` rules) — unchanged

The model checks business rules (`SimulationError`) and nothing about shape: an unknown key is a
`TypeError`, a string price crashes inside a validator, `true` simulates a R$ 1 apartment, `NaN`
flows into the payload. For the CLI, argparse was the shape layer; for the API the controller is,
and it runs before `input_from_dict`. `400` = "I could not build a simulation input" (client bug,
fix the request); `422` = "I built it and it describes an impossible contract" (user input, show
the message in the form). Strict types, no `null`-means-default and no unknown keys follow from
the same principle: every leniency hides a client bug behind a plausible number.

### 10. One error body: `error` + `code`, `field`/`index` when they apply; first rule wins

`error_to_dict` gave the shape its first key; the validators are designed to stop at the first
broken rule so the buyer sees the most fundamental problem, and the API keeps that for every
status. `422` messages are user-facing and pinned by Gherkin, so they are contractual. `400`
messages describe client bugs and are not — which is why revision 6 added `code` and `field`:
a client that has to *branch* on a `400` (a test, a form that highlights the offending input)
needs something stable that is not prose, and for shape errors the controller knows the exact
cause and key, unlike the model's `422`s. `code` is a flat `snake_case` string rather than RFC
9457 problem details because the four keys cover every need this API has and the CLI and the
API keep agreeing on `error`.

### 11. Unrounded floats, R$ as numbers, monthly rates as fractions — unchanged

The behave suite asserts to the cent against the same nodes; rounding in the API would make the
API and the CLI disagree on last digits. Presentation is the client's. Monthly rates are
fractions because that is what the model computes and a chart multiplies; inputs stay
percentages because that is how INCC and bank rates are quoted.

### 12. No `/v1`

One client ships with the backend. Additive changes (new keys, new nodes) are not breaking:
clients must ignore keys they do not know. Versioning arrives with the first incompatible change.

### 13. A comparison is a `GET` over simulations; `POST /api/comparisons` is a shortcut to it

The full evaluation is in [Which routes fit](#which-routes-fit--the-evaluation). In short: the
model says a comparison is `[simulate(i) for i in inputs]` — nothing of its own — so the API says
the same: no store, no id, a URL made of its members' ids, rows that link back to them. The
`POST` exists because the domain describes candidates as base + overrides and because the
reference run, the tests and scripts want one request; it returns exactly the `GET`
representation so there is one shape, not two.

### 14. Rows are flat, `summary_to_dict` plus `id`/`href`

A comparison is a table; every consumer (Gherkin, text report, grid) reads columns. Nesting
`summary` under each row (to mirror the simulation resource) would make `?fields=` select a
blob instead of columns and would change the view the behave suite pins. The two extra columns
cannot collide with the summary's names. The summary keeps its own vocabulary
(`balance_at_delivery`, not `corrected_balance`) because the feature tables pin it; the
column table is the bridge.

### 15. `POST /api/comparisons` is all-or-nothing and names the failing item

Every candidate (or variation) is validated and simulated before any is stored, so a client
never gets half a comparison. The `422` message stays verbatim (contractual, user-facing) and
the item's position travels in its own key, `index` — the front-end highlights the row, the
buyer reads the same sentence the CLI would print. One key serves both `candidates` and
`variations`: the client knows which array it sent.

### 16. A what-if is a comparison with `relative_to`

The full evaluation is in [Which routes fit](#which-routes-fit--the-evaluation-1). The model
already says it: a variation is `base.with_overrides(**v)` — a simulation — and `what_if_to_dict`
is summaries plus a subtraction. Everything a what-if adds (`overrides`, `delta`) is a pure
function of simulations that exist, given one reference id. One representation for "rows side
by side" keeps the front-end to one table component, keeps `fields` and `href` semantics in one
place, and gives the cash ladder, the INCC re-run and the "more cash" panel the same URL shape.

### 17. `overrides` is a diff of resolved inputs, not an echo of the request

Echoing what the client sent would tie the `GET` form to a `POST` (the `GET` has no request to
echo) and would report no-op overrides as changes. Diffing the two resolved inputs is always
available, always true, and makes the first rung of a cash ladder collapse onto the base instead
of pretending to be a variation. Labels are left to the client for the same reason: they are the
one thing that cannot be recomputed, so keeping them would force a store.

### 18. Variations are derived from a stored base, not an inline one

`POST /api/simulations/{id}/what-if` is the shape of the user's gesture — "this one, but with…"
— and the only way the client does not resend an input the server already holds. An inline
form (`relative_to` index on `POST /api/comparisons`) is recorded as a possible convenience,
not adopted, to avoid two creation paths for one `GET`.

### 19. The cash ladder gets a route after all — as a preset, not a representation

Revision 4 said "no route"; revision 5 reverses it, and the difference is what was being
evaluated. As a *response*, a ladder is a what-if and gains nothing from a shape of its own —
that verdict stands, and `POST …/cash-ladder` answers with the what-if `GET`. As a *request*,
a ladder has rules a generic what-if cannot state — ascending, distinct, non-negative amounts —
and the product names it everywhere (`--cash-ladder`, the Gherkin step, the front-end view,
the README's headline). A route that costs a three-line body and buys those rules and that
parity is worth having. A `GET` form was rejected because it would create simulations, and
the one rule this document holds to is that `GET` does not create.

## Open questions

Not decided here; none blocks the implementation.

- **Row ranges on arrays.** The stacked-bars chart wants months `0..N` of `timeline/months`
  (20 of 380 rows). A `?from=&to=` on array nodes (by `month`, not index) is the obvious
  addition; deferred until the front-end is being built, so the semantics match what it draws.
- **Multi-process deployment.** If one process is not enough, either a shared store (Redis,
  keyed by the same id — the contract does not change) or the stateless token id (decision 2,
  rejected alternative — the contract changes only in that ids get long).
- **List and delete.** `GET /api/simulations` (ids, names, `created_at`) and
  `DELETE /api/simulations/{id}`. With comparisons addressed by `ids`, a list would let a client
  rebuild a comparison after a page reload without keeping the ids; not needed before that.
- **Comparison columns.** The summary carries `cash_upfront` but not `fgts_upfront` (it was shaped
  for the cash ladder). Adding columns to `summary_to_dict` is additive; the cash ladder and the
  Gherkin tables would not notice. Decide when the front-end grid is designed.
- **`delta` columns.** `delta` subtracts every numeric summary column, including `list_price`,
  `months_remaining` and `peak_month`, which are rarely meaningful as differences. It mirrors
  `what_if_to_dict`; trimming it is additive-in-reverse (removing keys) and should be decided
  with the front-end panel.
- **Inline what-if.** `relative_to` as an index on `POST /api/comparisons` would give scripts a
  one-request what-if with an inline base. Not adopted; revisit on demand.
- **Generic sweep.** `…/cash-ladder` is a sweep over one field. When a second sweep is wanted (an
  INCC sweep is the candidate), consider `…/sweep` with `{"field", "values"}` and make
  `cash-ladder` its alias; the ladder's contract would not change.
- **The ladder's knee.** The amount at which the developer installment reaches zero (the
  remaining down payment) is where extra cash starts reducing the financed balance. A client can
  read it from `rows[*].developer_installment`; whether the response should name it is a
  front-end question.
- **Where `name`'s default lives.** Controller (as the CLI does today) or `ContractData`. Moving it
  to the DTO removes the only field both controllers special-case, and lets `GET /api/fields`
  report it without a special case too.
- **Field help text.** The CLI's `HELP` dict lives in `cli_controller.py`; `GET /api/fields` wants
  the same text. `dataclasses.field(metadata={"help": …, "unit": …})` on the DTOs would give both
  controllers one source.
- **Strictness of `input_from_dict`.** It coerces `balloon_months` items with `int()`. Under this
  contract the controller rejects non-integers first, so the coercion becomes dead code.
- **Per-rule `422` codes.** Every `422` has `code: "invalid_input"` because the model raises one
  exception type whose message is the contract. If the front-end ever localizes messages or
  highlights the field a business rule is about, `SimulationError` would need to carry a code
  and a field — a model change, additive on the wire.
- **Business ceilings.** The [API limits](#api-limits) are protective (`400`). A financing term
  above 420 months or a delivery more than, say, 60 months away is a business impossibility and
  would belong in the model's validators as a `422` with a message a buyer can read.

## Next steps

1. Implement `app/controllers/api_controller.py` and the store to this document;
   `tests/test_api_controller.py` with Flask's test client: each shape rule → `400`, one `422`,
   `POST` idempotency (same id), `404` after expiry, path walk and `fields` on an object and on an
   array, and byte-equality of `/result` with `simulation_to_dict`.
2. API-level behave features: an `HttpGateway` with the same interface as `EngineGateway`
   (`simulate(data)` = `POST` then `GET …/result`), so the existing scenarios run unchanged over HTTP.
3. `tests/test_api_controller.py` for comparisons: `GET` order and `fields`, `404` naming the
   missing id, `POST` merge (`base` vs candidate precedence), all-or-nothing with `index`, and equality of the `POST` body with `GET` on its `Location`. The behave `HttpGateway`'s
   `compare(rows)` = `POST /api/comparisons` with `base = {}` and the rows as candidates.
4. `tests/test_api_controller.py` for what-ifs: `relative_to` adds `overrides`/`delta` and the
   `relative_to` row; a no-op variation yields the base's id with `overrides: {}`; `delta`
   equals `what_if_to_dict`'s for the same inputs; empty variation → `400`; `404` on an unknown
   base before the body is read; the cash ladder example reproduces the Gherkin table.
5. `tests/test_api_controller.py` for ladders: the Gherkin ladder table reproduced from the
   `POST`; unsorted / repeated / negative amounts → `400` with the right `index`; a rung above the
   list price → `422` with `index`; equality of the ladder body with the same amounts sent as
   `…/what-if` variations.
6. `tests/test_api_controller.py` for errors: one test per `code` row of the status table; the
   order of checks (a body breaking several rules gets the first); every Flask-raised error is
   JSON with the right `code` (unknown route, `405` with `Allow`, `413`, `415`, malformed JSON);
   `X-Request-Id` echoed and generated; a forced exception in a view yields the constant `500`
   body with `request_id` and one `ERROR` log record, with `debug=True` and `False` alike; a
   `NaN` injected into a payload yields a `500`, not invalid JSON.
7. Implement in the order of this document: simulations, fields, comparisons, what-if,
   cash-ladder, errors last but tested throughout. `ROADMAP.md` is already aligned with these
   routes.
