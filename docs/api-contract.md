# SINCERO API contract

> **Superseded on 2026-11-09** by [engine-in-the-browser](decisions/engine-in-the-browser.md): the
> engine runs in the buyer's browser, so there is no server and no API. This contract (revision 7, and
> revision 6 before it) is kept as history and as the starting point of a future public API:
> [how to bring it back](plan/typescript-port.md#a-public-api-later). The `backend/` files it names are
> on the tag `python-engine-final` (and in `legacy/backend/`).

*Revision 7 — 2026-11-05. The API is the Connect service `sincero.Simulations`
([decision](decisions/api-protocol-and-language.md)). Supersedes revision 6, the REST API
(`/api/simulations`, `/api/comparisons`, `/api/fields`); the figures and the payload of a
simulation do not change, the surface does.*

The `.proto` files are the contract; this document explains them and records what a schema
cannot say. Where the two disagree the `.proto` wins and a test fails:

| Source | What it holds |
|---|---|
| [`backend/proto/sincero/simulation_input.proto`](../backend/proto/sincero/simulation_input.proto) | `SimulationInput` (the input fields, their defaults, groups and rules), `SimulationOverrides` (a part of an input) |
| [`backend/proto/sincero/simulation_result.proto`](../backend/proto/sincero/simulation_result.proto) | `SimulationResult` (every figure of a simulation), `Summary` (one row of a comparison) |
| [`backend/proto/sincero/simulations_service.proto`](../backend/proto/sincero/simulations_service.proto) | `service Simulations`, its requests and responses; states the revision of this document |
| `backend/proto/google/rpc/error_details.proto` | `ErrorInfo`, `BadRequest`: the error details (vendored from googleapis) |

The code generated from them (`make proto`) is `backend/app/gen/` (Python) and
`frontend/src/gen/` (TypeScript). Tests: `tests/test_api_contract.py` (this document against
the descriptors), `tests/test_service_definition.py` (the service and the result messages
against the views), `tests/test_simulation_overrides.py`, `tests/test_connect_errors.py`,
`tests/test_gen_proto.py` (the generated code is fresh).

## Transport

- **Protocols.** Connect, gRPC and gRPC-Web, from one ASGI application (`connectrpc`); a
  browser uses Connect or gRPC-Web (`@connectrpc/connect-web`). No proxy.
- **Paths.** `POST /sincero.Simulations/<Rpc>`. The RPCs marked `NO_SIDE_EFFECTS` are also
  served as `GET /sincero.Simulations/<Rpc>?connect=v1&encoding=json&message=<request>`, which
  a Connect client uses for them: cacheable reads.
- **Encodings.** Protobuf binary or JSON (proto3 JSON mapping). In JSON:
  - field names are accepted as written in the `.proto` (`list_price`) or in lowerCamelCase
    (`listPrice`); responses use lowerCamelCase;
  - numbers may be sent as JSON strings (`"440000"`); a fractional value for an integer field
    or a `null` inside a list is refused by the mapping;
  - `null` means "not set", never a value (see [Partial inputs](#partial-inputs) for how to
    send "no balloons" and "back to null");
  - **unknown keys are refused**: the server configures its JSON codec with
    `ignore_unknown_fields=False` (the proto3 default ignores them).

## RPCs

| RPC | Request | Response | HTTP | Replaces (revision 6) |
|---|---|---|---|---|
| `CreateSimulation` | `SimulationInput` | `CreateSimulationResponse` | POST | `POST /api/simulations` |
| `GetSimulation` | `GetSimulationRequest` | `Simulation` | GET | `GET /api/simulations/{id}[/{path}]` |
| `GetComparison` | `GetComparisonRequest` | `Comparison` | GET | `GET /api/comparisons?ids=…&relative_to=…` |
| `CreateComparison` | `CreateComparisonRequest` | `Comparison` | POST | `POST /api/comparisons` |
| `CreateWhatIf` | `CreateWhatIfRequest` | `Comparison` | POST | `POST /api/simulations/{id}/what-if` |
| `CreateCashLadder` | `CreateCashLadderRequest` | `Comparison` | POST | `POST /api/simulations/{id}/cash-ladder` |
| `ListFields` | `ListFieldsRequest` | `ListFieldsResponse` | GET | `GET /api/fields` |

- **Ids.** A simulation's id is derived from its *resolved* input (defaults applied, `name`
  resolved): the same input always gets the same id, and creating it again is harmless.
- **All or nothing.** `CreateComparison`, `CreateWhatIf` and `CreateCashLadder` simulate every
  item before storing any; the first failure ends the request with its `index`
  ([Errors](#errors)).
- **Projections.** `GetSimulation.read_mask` names paths of `Simulation` (`summary`,
  `result.mortgage`, `result.timeline.peak_month`); empty returns all of it, `id` is always
  returned. It replaces revision 6's `{path}` and `?fields=`. `GetComparison.read_mask` names
  paths of `Summary`, applied to every row's `summary` and `delta`.

## Inputs

`SimulationInput` is one flat message; the split into three DTOs (contract, market, bank credit)
is a model concern, carried by the `(sincero.field)` option and not visible on the wire.
`ListFields` returns this table (`FieldSpec`), so a form needs no copy of it.

| Field | Group | Type | Required | Default | Unit |
|---|---|---|---|---|---|
| `name` | contract | string | no | `"CUSTOM"` | |
| `list_price` | contract | number | yes | | R$ |
| `months_remaining` | contract | integer | yes | | months |
| `down_payment_pct` | contract | number | no | `20.0` | % of list price |
| `fgts_upfront` | contract | number | no | `0.0` | R$ |
| `cash_upfront` | contract | number | no | `0.0` | R$ |
| `developer_installment` | contract | number\|null | no | `null` | R$ per month |
| `balloon_months` | contract | integer[] | no | `[]` | months |
| `incc_rate_pa` | market | number | no | `7.0` | % per year |
| `bank_rate_pa` | market | number | no | `10.26` | % per year |
| `term_months` | market | integer | no | `360` | months |
| `itbi_pct` | market | number | no | `2.0` | % of list price |
| `registry_pct` | market | number | no | `0.5` | % of list price |
| `income_commitment_ratio` | market | number | no | `0.3` | ratio 0-1 |
| `pre_approved_credit` | bank_credit | number\|null | no | `null` | R$ |
| `pro_soluto_months` | bank_credit | integer | no | `12` | months |

- **Required** fields are `optional` + `(buf.validate.field).required`: absent and invalid are
  different violations ([decision](decisions/required-fields-explicit-presence.md)).
- **`null`** (`developer_installment`, `pre_approved_credit`): an unset field; the model sizes
  the installment (the remaining down payment in equal parts) or takes the nominal balance as the
  pre-approved credit.
- **`name`**: the empty string is the unnamed simulation; the service resolves it to `"CUSTOM"`
  ([open question](#open-questions)).

## Partial inputs

The `base` and `candidates` of `CreateComparison`, the `variations` of `CreateWhatIf` and the
`overrides` of a comparison row are `SimulationOverrides`: the fields of `SimulationInput`, every
one optional and validated when set, with the same rules minus `required`. A field that is set
replaces the value it is merged onto; a field that is not set keeps it.

- **Candidates**: each is `{**base, **candidate}`; `list_price` and `months_remaining` must come
  from the candidate or from `base`.
- **Variations**: each is `stored_simulation.with_overrides(**variation)` and must set at least
  one field (`{}` would be the stored simulation itself). A variation equal to the base is valid
  and yields the base's own id.
- **Two fields need more than "set or not"**, because proto3 cannot tell an empty list or `null`
  from "not set":

| Field | Type in `SimulationOverrides` | JSON | Means |
|---|---|---|---|
| `balloon_months` | `BalloonMonths` | `{"months": [6, 12]}` | these balloon months |
| | | `{}` | no balloons |
| `developer_installment`, `pre_approved_credit` | `NullableAmount` | `{"value": 2500}` | this amount |
| | | `{}` | `null`: the model sizes it |
| any | | key omitted, or `null` | keep the value |

## Results

- `Simulation` is `{id, summary, result}`.
- `SimulationResult` has the ten sections of the JSON view (`simulation_to_dict`), field by
  field: `input` (resolved), `rates`, `down_payment`, `mortgage`, `construction_interest`,
  `closing_costs`, `financing` (`sac`, `price`), `credit_gap`, `total_cost`, `timeline`.
- `Summary` is `summary_to_dict`: the flat figures a comparison puts side by side.
- Money is R$; `*_pm` rates are monthly fractions; `*_pct` is 0-100. Proto3 omits zero values
  in JSON; a client reads them as 0.

## Comparisons

A what-if is a comparison with a reference ([decision](decisions/what-if-as-comparison.md)).

- `rows` are in the order asked (`ids`, `candidates`, `variations`, `amounts`).
- `relative_to` is set for `CreateWhatIf`, `CreateCashLadder` and a `GetComparison` with
  `relative_to`: the reference, row-shaped. Every row then carries
  - `overrides`: the input fields in which the row's resolved input differs from the
    reference's, with the row's values (a `SimulationOverrides`; a no-op override is not a
    difference);
  - `delta`: row minus reference for every number of `Summary` (`name` is empty).
- Labels are not on the wire: the client renders a variation from its `overrides` and
  `ListFields` (name, unit).

## Cash ladders

`CreateCashLadder` is a what-if preset: rung *i* is the stored simulation with
`cash_upfront = amounts[i]`. `amounts`: 1 to 20, each `>= 0` and `<= 10^12`, **strictly
increasing** (a rule of the service: `buf.validate` cannot compare an item with the one before).
The response is the what-if's, relative to the stored simulation.

## Validation

Three layers, in order; the first layer that fails ends the request.

| Layer | Rules | Failure |
|---|---|---|
| The proto3 JSON mapping / binary decoding | types, unknown keys | `invalid_argument`, the codec's message |
| `buf.validate` rules of the request (`protovalidate`) | required fields; ranges; list sizes; merged-input rules | `invalid_argument` + `BadRequest` |
| The model (`SimulationError`) | everything about the values together (FGTS + cash above the list price, balloons after delivery, …) | `invalid_argument` + `ErrorInfo` |

`buf.validate` rules of the requests (rule ids as they appear in `BadRequest.field_violations[].reason`):

| Where | Rule | Rule id |
|---|---|---|
| `SimulationInput.list_price` | required, `> 0` | `required`, `double.gt` |
| `SimulationInput.months_remaining` | required, `1..600` | `required`, `int32.gte_lte` |
| `SimulationOverrides.list_price`, `.months_remaining` | the same ranges, when set | `double.gt`, `int32.gte_lte` |
| `GetSimulationRequest.id`, `CreateWhatIfRequest.id`, `CreateCashLadderRequest.id`, `GetComparisonRequest.relative_to` | not empty | `string.min_len` |
| `GetComparisonRequest.ids`, `CreateComparisonRequest.candidates`, `CreateWhatIfRequest.variations`, `CreateCashLadderRequest.amounts` | 1 to 20 items | `repeated.min_items`, `repeated.max_items` |
| `CreateComparisonRequest` | every candidate has `list_price` / `months_remaining`, its own or `base`'s | `candidates.list_price`, `candidates.months_remaining` |
| `CreateWhatIfRequest.variations[]` | sets at least one field | `variation.not_empty` |
| `CreateCashLadderRequest.amounts[]` | `0..10^12` | `double.gte_lte` |

## Errors

Connect error codes, with the protocol's JSON body `{code, message, details}`; HTTP statuses
follow the protocol's mapping (`invalid_argument` is 400, `not_found` 404).

| Cause | Code | Detail |
|---|---|---|
| a `buf.validate` rule of the request | `invalid_argument` | `google.rpc.BadRequest`: one `field_violations[]` per rule broken: `field` (`variations[0].months_remaining`; empty for a rule of the whole request), `description`, `reason` (the rule id) |
| a rule of the model (`SimulationError`) | `invalid_argument` | `google.rpc.ErrorInfo`: `reason` `invalid_input`, `domain` `sincero`, `metadata.index` for the item of a comparison, what-if or ladder; the model's message verbatim as the error `message` |
| an unknown simulation id | `not_found` | none; message `simulation not found: <id>` |
| an undecodable body, an unknown JSON key | `invalid_argument` | none; the codec's message |
| an RPC the server does not implement | `unimplemented` | none |
| a request body over the server's limit | `resource_exhausted` | none |
| anything else | `internal` | none |

A client branches on the detail type: `BadRequest` marks a field of the form, `ErrorInfo` shows
the message. Both are `invalid_argument` because neither depends on the state of the service;
`failed_precondition` ("retry after fixing the state") is kept for a state the service does not
have yet. The mapping is `app/controllers/connect_errors.py`.

Revision 6 → 7:

| Revision 6 (REST) | Revision 7 (Connect) |
|---|---|
| `400` shape rules, `code`/`field`/`index` | the JSON mapping + `buf.validate`; `invalid_argument` + `BadRequest` |
| `422 invalid_input` with the model's message | `invalid_argument` + `ErrorInfo` (`reason: invalid_input`), the same message |
| `404` | `not_found` |
| `405`, `413`, `415`, `500` | Connect codes (`unimplemented`, `resource_exhausted`, `internal`) with the protocol's JSON body; the HTTP status follows the protocol's mapping |
| `Location` | none: the response carries the id |
| `X-Request-Id` | an interceptor, unchanged header |

## API limits

Upper bounds that keep one request bounded in time and size; not business rules (the model bounds
the inputs from below).

| Limit | Value | Enforced by |
|---|---|---|
| items in `ids`, `candidates`, `variations`, `amounts` | 1 to 20 | `.proto` |
| `months_remaining` | `<= 600` | `.proto` |
| a ladder amount | `<= 10^12` | `.proto` |
| `term_months`, `pro_soluto_months` | `<= 600` | service (`api_requests.UPPER_BOUNDS`) until moved to the `.proto` |
| money fields (`list_price`, `fgts_upfront`, `cash_upfront`, `developer_installment`, `pre_approved_credit`) | `<= 10^12` | service, idem |
| percentages (`down_payment_pct`, `itbi_pct`, `registry_pct`, `incc_rate_pa`, `bank_rate_pa`) | `<= 1000` | service, idem |
| `balloon_months` | at most 60 | service, idem |

## Open questions

- **Field help text.** Units live in `api_requests.UNITS`, help text in `cli_controller.HELP`;
  whether they move into the `.proto` (a `(sincero.field)` member) is open.
- **Where `name`'s default lives.** `"CUSTOM"` is the service's and the CLI's, not the model's;
  moving it into the `.proto` would reorder the generated dataclass
  ([decision](decisions/input-fields-from-proto.md)).
- **API ceilings in the `.proto`.** The limits marked "service" above are still
  `api_requests.py`'s; moving them to `buf.validate` rules on `SimulationInput` and
  `SimulationOverrides` retires the last of the shape layer.
- **`delta` of non-additive columns.** `delta` subtracts `list_price`, `months_remaining` and
  `peak_month` too, as `what_if_to_dict` does; trimming it is for the front-end panel to decide.
- **Lifetime of stored simulations.** Not restated in this revision.

## Revision history

| Revision | Change |
|---|---|
| 7 | The Connect service replaces the REST surface; typed results (`SimulationResult`, `Summary`) and `read_mask` replace `{path}` and `?fields=`; partial inputs are `SimulationOverrides`; errors are Connect codes with `BadRequest` / `ErrorInfo` details |
| 6 | REST API: simulations, comparisons, what-ifs, cash ladders, fields |
| 5 | Cash ladders on top of what-ifs |
| 4 | A what-if is a comparison with a reference |
