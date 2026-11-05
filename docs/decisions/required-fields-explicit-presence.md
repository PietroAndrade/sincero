# Decision: a required input field has explicit presence — `optional` + `buf.validate` `required`

*Status: accepted, 2026-11-04. Applied to the experiment's rules,
[`../experiments/protobuf-languages/proto/sincero_rules.proto`](../experiments/protobuf-languages/proto/sincero_rules.proto),
and pinned by the Python and TypeScript runs of the experiment; applied to
[`backend/proto/sincero/simulation_input.proto`](../../backend/proto/sincero/simulation_input.proto)
in task 5.3c (2026-11-04; see [Not done yet](#not-done-yet)). Supersedes section 3 ("The 'absent' trap") of
[api-protocol-and-language](api-protocol-and-language.md), which chose plain scalars and a rule
that rejects their zero value.*

## Context

The API validates its requests with `buf.validate` rules enforced by `protovalidate`
([api-protocol-and-language](api-protocol-and-language.md)). A body without `list_price` or
`months_remaining` must be refused by those rules, and the model must never run for it. The same
goes for a body where either field is `0`. The question was how to protect a required field from
being absent.

In proto3 a plain scalar has **implicit presence**. `{}`, `{"months_remaining": null}` and
`{"months_remaining": 0}` parse to the same message, and none of them puts a byte on the wire.
`protovalidate` therefore never sees "absent"; it sees `0`. The earlier choice relied on that: for
a field whose zero is never valid, a rule that rejects `0` also rejects "absent". That protects
`list_price` (`gt: 0`) and `months_remaining` (`gte: 1`), but has two problems:

1. **The refusal does not say what is wrong.** A missing `months_remaining` is refused as
   "must be greater than or equal to 1 and less than or equal to 600". The contract tells the
   two apart ([`../api-contract.md`](../api-contract.md): `missing_field` vs `out_of_range`), and
   a client cannot.
2. **It only works while zero is invalid.** A required field whose zero is a valid value cannot
   be protected at all: an absent field is accepted (variant F below). The earlier decision could
   only say that such a field must not be required.

## Decision

Every required field of a request message is declared `optional` (explicit presence) **and**
carries `(buf.validate.field).required = true`, next to its range rule:

```proto
optional double list_price = 1 [(buf.validate.field).required = true, (buf.validate.field).double.gt = 0];
optional int32 months_remaining = 2 [(buf.validate.field).required = true,
                                     (buf.validate.field).int32 = {gte: 1, lte: 600}];
```

| Required field | Declared as | Absent or `null` | Invalid value |
|---|---|---|---|
| `list_price` | `optional double`, `required`, `double.gt = 0` | `value is required` (rule `required`) | `0`, negative: `must be greater than 0` (rule `double.gt`) |
| `months_remaining` | `optional int32`, `required`, `int32 = {gte: 1, lte: 600}` | `value is required` (rule `required`) | `0`, `5000`: `must be greater than or equal to 1 and less than or equal to 600` (rule `int32.gte_lte`) |
| `name` | unchanged: no rule | the empty string is the unnamed simulation, resolved to `"CUSTOM"`; absent and `""` mean the same thing, so presence is not needed | — |

In a proto with this rule, `optional` means "has presence". It no longer means "may be omitted"
— `required` says whether a field may be omitted.

A message-level CEL rule that reads a required field guards it with `has()`, so an absent field is
reported once, by `required`, and not again as a value of `0`:

```proto
expression: "!has(this.list_price) || this.fgts_upfront + this.cash_upfront <= this.list_price"
```

Without the guard, `{"months_remaining": 19, "fgts_upfront": 13000}` gets a second, misleading
violation, "upfront payments exceed the list price", next to `list_price: value is required`
(checked while writing this decision).

## Evidence

Each variant is one message of
[`presence_variants.proto`](../experiments/protobuf-languages/proto/presence_variants.proto),
parsed from JSON as a Connect server parses it and validated by `protovalidate` 2.1
([`presence-output.txt`](../experiments/protobuf-languages/python/presence-output.txt)):

| Variant | `{}` / `null` | `0` | valid | Verdict |
|---|---|---|---|---|
| **A.** plain + `gte: 1` (the earlier choice) | refused: range message | refused: range message | accepted | protects only because 0 is invalid; absent looks like 0 |
| **B.** plain + `required` | refused: `value is required` | refused: `value is required` | accepted | the same conflation, with the other message; on a plain field `required` means "not 0" |
| **C.** `optional` alone | **accepted** | refused: range message | accepted | **the trap**: the rules of an unset field are skipped, so an absent field gets through |
| **D.** `optional` + `required` | refused: `value is required` | refused: range message | accepted | **chosen**: the only variant that tells absent from invalid |
| **E.** plain + CEL `has(this.x)` | refused: both messages | refused: both messages | accepted | on a plain field `has()` means "not 0"; no gain over A |
| **F.** plain, zero is valid (`gte: 0`) | **accepted** | accepted | accepted | a plain field cannot be protected when 0 is valid |
| **G.** `optional` + `required`, zero is valid | refused: `value is required` | accepted | accepted | D covers this case too |

On the wire, D sends an explicit `0` (2 bytes), so a zero is not lost between client and server
(`HasField` is `True` after a binary round trip). Under A the zero is not encoded (0 bytes) and
the JSON serializer omits it too. Omitting it is how `months_remaining: 0` became a `500` in the
Connect experiment, where `to_json()` dropped it before the model
([`../experiments/protobuf-languages/connect/README.md`](../experiments/protobuf-languages/connect/README.md)).

The rules refuse an absent or zero required field **before the model runs**.
`simulate_if_valid` in [`rules.py`](../experiments/protobuf-languages/python/rules.py) runs the
`.proto`'s rules first and calls the model only for a body they accept. The tests spy on
`OffPlanSimulator.run`, the only place the model's calculations are built. For nine bodies
(`{}`; a single field missing; `0`, `0.0` or `null` in either field; both `0`) the rules refuse
the body and `run` is never entered. A valid body enters it once.

Run it:

```bash
cd backend
.venv/bin/python -m pytest ../docs/experiments/protobuf-languages/python -q -p no:cacheprovider   # 27 tests
.venv/bin/python ../docs/experiments/protobuf-languages/python/presence.py                       # the table above
.venv/bin/python ../docs/experiments/protobuf-languages/python/rules.py
cd ../docs/experiments/protobuf-languages/typescript && npm test                                  # 8 tests
```

`test_a_required_field_absent_is_refused_as_required_and_zero_as_out_of_range` (Python) and
`a required field absent is refused as required, and 0 as out of range` (TypeScript) fail when
`sincero_rules.proto` is put back to variant A (checked). So they pin this decision, not just the
rules. The "before the model" tests pass under A as well, as they should: A also refuses these two
fields, it just cannot say why.

## Reason

- D is the only variant that refuses an absent field and an invalid one with **different**
  violations. `rule_id` is `required` for the first and `double.gt` / `int32.gte_lte` for the
  second, so a server can map them to the contract's `missing_field` and `out_of_range` without
  parsing messages.
- D does not depend on the zero being invalid (G), so a future required field does not need a
  special case or a ban.
- D keeps the explicit zero on the wire, which removes the class of bug the Connect experiment
  hit.
- C is what "make it `optional`" means if `required` is forgotten, and it is worse than doing
  nothing: a missing field passes silently. The rule is therefore always `optional` **and**
  `required`, never one without the other.

## Consequences

- **Generated TypeScript.** `listPrice` and `monthsRemaining` become `listPrice?: number | undefined`
  in `sincero_rules_pb.ts` (regenerated with `npm run generate:rules`). Client code must handle
  `undefined`, which is what the field really can be before validation.
- **Generated Python.** `HasField("list_price")` is available. Reading an unset field still gives
  `0.0`, so code must check presence (or validate) before it trusts the value.
- **CEL rules** that read a required field need the `has()` guard shown above.
- **`required` is enforced by `protovalidate`, not by the parser.** A server that parses a message
  and skips validation gets no protection from this decision. The order is: parse, validate, then
  the model.

## Rejected

- **A — plain scalar + zero-rejecting rule** (the earlier choice): the refusal does not say
  "required", and it cannot protect a field whose zero is valid.
- **B — plain scalar + `required`**: the same conflation; the range rule's message never shows.
- **C — `optional` alone**: lets an absent field through.
- **E — plain scalar + CEL `has()`**: on implicit presence `has()` is "not 0", so it adds a second
  message and no information.
- **Converting field by field against the descriptor's presence**, as the Connect experiment's
  `to_model_input` does: it is a fix in the server's glue, not in the contract, and every server
  and client would have to repeat it.

Not evaluated: wrapper types (`google.protobuf.Int32Value`) and Protobuf Editions'
`features.field_presence`. Both give presence too, but change the JSON shape or the file syntax of
every schema that uses them.

## Not done yet

Found while gathering the evidence. None of these changed in this decision, because the changes
belong to files outside the experiment:

1. **(Rules now on the real message; server change left to M5.) The Connect experiment's server does not enforce these rules.**
   [`connect_server.py`](../experiments/protobuf-languages/connect/server/connect_server.py)
   calls `protovalidate.validate(request)` on `sincero.SimulationInput`, which has no
   `buf.validate` rules, so `{}` and `{"list_price": 0, "months_remaining": 0}` pass it. The
   refusal in [`connect/output.txt`](../experiments/protobuf-languages/connect/output.txt) comes
   from the model (`simulate`), not from the `.proto`. The rules have to be validated before
   `simulate`, as `simulate_if_valid` does.
2. **`sincero.rules.ValidatedInput` cannot validate a binary request.** Its field numbers differ
   from `sincero.SimulationInput`'s (`list_price` 1 vs 2, `months_remaining` 2 vs 3), so the bytes
   of a valid `SimulationInput` read as an empty `ValidatedInput`. Only a JSON body can be checked
   against the copy. The lasting fix is to put the rules on `SimulationInput` itself.
3. **Done in 5.3c: `backend/proto/sincero/simulation_input.proto` declared the required fields plain.**
   Applying D there was tried on copies, without changing the backend (2026-11-04):
   - **As it is, the generator cannot take it.** `tools/gen_dto.py`'s `compile_proto` passes only
     `-I` paths, so `import "buf/validate/validate.proto"` fails (`File not found`): the repository
     holds `buf/validate` only as the descriptor set `buf_validate.binpb`. With the import resolved
     (`--descriptor_set_in`, as the experiment's `_setup.py` does), the generator refuses D on its
     own convention: `list_price: optional, but neither a default nor nullable — what does
     omitting it mean?`. Either way 5 of the 19 tests of `tests/test_gen_dto.py` break, so
     `make dto` and `make test` would fail.
   - **One rule makes it fit.** `optional` + `(buf.validate.field).required = true` produces a
     required dataclass field (`list_price: float`, no default), and `required` together with a
     default or `nullable` is refused as a contradiction. The rest stays as it is: a range rule
     alone does not make a field required, and a required field after an optional one is still
     refused. With that rule and `buf/validate` resolvable, the generated `input_fields.py` is
     **byte-identical** to the committed one. The dataclasses, the DTOs and `backend/app` do not
     change, and the 19 tests of `test_gen_dto.py` pass, plus 6 new cases for the rule.
   - **At runtime,** `protovalidate.validate` on the real `sincero.SimulationInput` then refuses
     `{}`, `null` and zeros, which closes item 1 by itself. If validation were skipped, an absent
     field does not become `0`: building `ContractData` fails (`missing 2 required positional
     arguments`). That is a `500`, but a loud one — validation has to run first.
   - **Every `protoc` call on `simulation_input.proto` needs `buf/validate`:** the generator, the
     experiments' `_setup.py` (checked: the same `File not found`), the TypeScript `buf generate`
     and the Connect `generate.sh`. A `buf.yaml` dependency on `buf.build/bufbuild/protovalidate`
     or the descriptor set on each path would both work.
