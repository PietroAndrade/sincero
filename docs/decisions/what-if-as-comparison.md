# Decision: a what-if is a comparison with a reference row, not an endpoint of its own

> **Superseded for the API on 2026-11-09** by [engine-in-the-browser](engine-in-the-browser.md): there
> are no endpoints. The idea stands in the engine: a what-if is the base and its variations, each
> row's `delta` relative to the base (`whatIf`, `cashLadder` and `whatIfToDict` in `engine/src/`).

*Status: accepted in revision 4 of [`docs/api-contract.md`](../api-contract.md) (milestone 5,
not yet implemented). Revision 5 built the cash ladder on top of it.*

## Context

The roadmap planned four RPC-style endpoints for the Flask API — `POST /api/simulate`,
`/api/compare`, `/api/what-if`, `/api/cash-ladder` — each taking inputs and returning the
corresponding JSON view (`simulation_to_dict`, `comparison_to_dict`, `what_if_to_dict`). The
what-if view is the richest of the three:

```python
what_if(base, {"INCC 4%": {"incc_rate_pa": 4.0}, "R$ 30k cash": {"cash_upfront": 30_000}})
# -> {"base": summary, "scenarios": [{"label", "overrides", "summary", "delta"}, ...]}
```

While specifying the API, `POST /api/simulate` was replaced by a **simulation resource**
(`POST /api/simulations` creates; `GET /api/simulations/{id}/{path}` reads one node of the
payload) because the one-shot payload is 180 KB and a screen needs a few KB of it. The id of a
simulation is a hash of its resolved input. `/api/compare` then became `GET /api/comparisons?ids=…`
— a *view* over stored simulations, rows linking back to them — with `POST /api/comparisons` as
a shortcut that creates the members and answers with the `GET`.

The question for `/api/what-if` was whether it is a third kind of thing or the same kind again.

## Decision

1. **No `/api/what-if` route.** A what-if is `GET /api/comparisons?ids=…&relative_to={id}`: the
   comparison whose rows are measured against one stored simulation. `relative_to` adds the
   reference as a row-shaped object and gives every row two derived columns:
   - `overrides` — the input fields in which the row's *resolved* input differs from the
     reference's, with the row's values;
   - `delta` — row minus reference for every numeric summary column, the arithmetic of
     `what_if_to_dict`.
2. **Variations are created from a stored base**: `POST /api/simulations/{id}/what-if` with
   `{"variations": [{overrides}, …]}` creates one simulation per variation
   (`base.with_overrides(**v)`), all-or-nothing, and answers with the `GET` above (`201`,
   `Location` = that URL).
3. **Labels are not on the wire.** The model keys variations by a display label (`"INCC 4%"`);
   the API identifies a variation by its `overrides`.
4. `what_if`, `cash_ladder` and `what_if_to_dict` are unchanged; the CLI keeps using them. The API
   reaches the same figures through `with_overrides` + `simulate`, which is all they do.

## Reason

- **The model already says so.** A variation *is* a simulation — `base.with_overrides(**v)` —
  and `what_if_to_dict` is summaries plus a subtraction. Everything a what-if adds is a pure
  function of simulations that exist, given one reference id. Making it a resource or an RPC
  would store or recompute what the simulation resource already holds.
- **Rows must link to simulations.** The front-end's what-if panel ("what changes if…") needs to
  drill from a row into its timeline and schedules. An RPC answer has no ids; a comparison row
  has `id` and `href`.
- **One table component.** Candidates side by side and variations side by side are the same
  grid with two extra columns. One representation means one `fields` mechanism, one `href`
  convention, one test fixture.
- **`overrides` as a diff, not an echo.** The `GET` form has no request to echo, so the column
  must be computable from the stored inputs; diffing resolved inputs is always available and
  always true (a no-op override is not a change). It also makes the first rung of a cash ladder
  collapse onto the base instead of pretending to be a variation.
- **Labels would force a store.** They are the one part of `what_if_to_dict` that cannot be
  recomputed from the simulations. Keeping them would turn a what-if into a stored resource with
  its own lifetime, only to remember presentation text the client can render from `overrides`
  and `GET /api/fields` (name, unit).
- **Derive from the stored base, do not resend it.** `POST /api/simulations/{id}/what-if` is the
  shape of the user's gesture — "this one, but with…" — and the base is already on the server.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| `POST /api/what-if` (base input + labelled variations → `what_if_to_dict`) | no ids, base simulated again while it is on screen, a third response shape |
| A stored what-if resource (`POST /api/what-ifs` → `GET /api/what-ifs/{id}`) | its state is a reference id + ordered ids (fits a URL) + labels (presentation) |
| `relative_to` as an index on `POST /api/comparisons` (inline base) | a second creation path for the same `GET`; needs an awkward `{}` candidate; revisit on demand |

## Consequences

- The ROADMAP's milestone 5 names the routes of the contract (`/api/simulations`,
  `/api/comparisons`, `…/what-if`, `…/cash-ladder`, `/api/fields`) instead of the four RPCs.
- Errors about one variation carry `"index": i` next to the verbatim `error` message; the same
  key serves comparisons (`candidates[i]`) and ladders (`amounts[i]`).
- An empty variation `{}` is `400` (a request for the base itself is a client bug); a variation
  equal to the base is valid and yields the base's own id with `overrides: {}`.
- The front-end renders labels itself. `GET /api/fields` provides the field names and units it
  needs to do so.
- The cash ladder became `POST /api/simulations/{id}/cash-ladder`, a validated preset over this
  what-if (ascending, distinct, non-negative amounts); its response is the what-if's. See the
  contract's [Cash ladders](../api-contract.md#cash-ladders).
- `delta` mirrors `what_if_to_dict` and therefore subtracts `list_price`, `months_remaining` and
  `peak_month` too; trimming it is an open question for the front-end panel.
- The behave `HttpGateway` does not need a what-if method: the "re-runs the simulation with…"
  scenarios run as two simulations, exactly as `support/world.py` does today.
