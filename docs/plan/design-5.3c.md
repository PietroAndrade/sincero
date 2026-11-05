# Design: 5.3c, the presence rule on the real input

Status: design, 2026-11-04, for branch `feat/presence-rule-real-input`. Task:
[tasks.md](../../tasks.md) 5.3c. Decision it applies:
[required-fields-explicit-presence](../decisions/required-fields-explicit-presence.md) (variant D),
whose "Not done yet" item 3 already tried this change on copies of the files. This document turns
that trial into steps.

## Goal

`backend/proto/sincero/simulation_input.proto` declares `list_price` and `months_remaining` as
`optional` + `(buf.validate.field).required = true`, with their range rules. The generated
`app/models/input_fields.py` does not change by a byte, and `protovalidate` on the real
`SimulationInput` refuses an absent, `null` or zero value of either field, with "absent" and
"zero" as different violations.

## Out of scope

- The other model rules and API ceilings as `buf.validate` constraints, and the CEL cross-field rule
  (5.5). Only the two range rules that "refuses zeros" needs are added here.
- Calling `protovalidate` on the request path: there is no server yet (5.6).
- Making the Connect experiment's server validate before `simulate` (decision, "Not done yet" item 1):
  it closes by itself once the real message has rules, but changing `connect_server.py` stays out.
- `name`: stays a plain `string`; absent and `""` both mean the unnamed simulation.

## Today

| Piece | State |
|---|---|
| `simulation_input.proto` | `list_price` (`double`) and `months_remaining` (`int32`) are plain scalars, no `buf.validate` import |
| `tools/gen_dto.py` | plain scalar → required field; `optional` → must have a `default_*` or `nullable`, otherwise `optional, but neither a default nor nullable` |
| `compile_proto` | `protoc -I<include>… -I<grpc_tools/_proto>`: no way to resolve `buf/validate/validate.proto` |
| `buf/validate` in the repo | only `docs/experiments/protobuf-languages/proto/buf_validate.binpb`, a descriptor set taken from `@bufbuild/protovalidate` |
| `protovalidate` (Python) | 2.1.0 installed in `backend/.venv`, **not** in `requirements-dev.txt` |

## Design

### 1. Where `buf/validate/validate.proto` comes from

**Decision: move the descriptor set to `backend/proto/buf_validate.binpb`** and have every `protoc`
call pass `--descriptor_set_in=<that file>`. The experiments point to it instead of keeping their own
copy.

| Option | For | Against |
|---|---|---|
| **Descriptor set in `backend/proto/`** (chosen) | Works offline with `grpcio-tools`' `protoc`, which `make dto` already uses; the experiments already prove it; one file | A binary in the repo; its protovalidate version has to be written down |
| `buf.yaml` dependency on `buf.build/bufbuild/protovalidate` | The standard way; `buf` resolves and pins it | Needs network and the `buf` CLI for `make dto` and `make test`; `grpcio-tools`' `protoc` can't use it |
| Vendor `validate.proto` source under `backend/proto/buf/validate/` | Readable, plain `-I` | `buf generate` on `backend/proto` would also generate it for TypeScript, clashing with `@bufbuild/protovalidate`'s own copy |

Write the version down in a short `backend/proto/README.md` ("extracted from
`@bufbuild/protovalidate` 1.3; replace by a `buf.yaml` dependency when M5 adds `buf`"). 5.4 can
revisit this when it introduces `make proto`.

### 2. The `.proto`

```proto
import "buf/validate/validate.proto";

// List price, R$.
optional double list_price = 2 [(sincero.field) = {group: CONTRACT},
                                (buf.validate.field).required = true,
                                (buf.validate.field).double.gt = 0];
// Months left until the building is delivered (time left, not the project's total duration).
optional int32 months_remaining = 3 [(sincero.field) = {group: CONTRACT},
                                     (buf.validate.field).required = true,
                                     (buf.validate.field).int32 = {gte: 1, lte: 600}];
```

The range rules are needed because `required` on an `optional` field means "present": a present `0`
passes `required` and is refused only by the range rule. The bounds are the decision's
(`gt: 0`, `1..600`); 600 is the API ceiling from `docs/api-contract.md`.

Update the header's conventions to match:

- *A plain scalar becomes a required dataclass field; on the wire it can't be told apart from its
  zero value. Use it only when absent and zero mean the same thing (`name`).*
- *A field that must be present is `optional` + `(buf.validate.field).required = true`: a required
  dataclass field, and on the wire "absent" is refused apart from "invalid". Never `optional`
  without `required`, a default or `nullable`.*
- *An `optional` field that may be omitted says what omission means: a `default_*` or `nullable`.*

### 3. `tools/gen_dto.py`

**`compile_proto`.** Add `--descriptor_set_in=PROTO_DIR/buf_validate.binpb` and list
`buf/validate/validate.proto` as a second file to compile, so that `buf/validate/validate_pb2.py` is
generated into the temporary directory next to `sincero/simulation_input_pb2.py`. Importing the
latter imports the former, which registers the `buf.validate.field` extension in the default pool.
The experiments' `_setup.py` does the same thing, so it is known to work.

`--include_imports` together with `--descriptor_set_out` then also puts `validate.proto` in the
returned set. `read_groups` looks the file up by name, so the extra file does no harm.

**`read_groups`.** Read the `buf.validate` rule next to `(sincero.field)`:

```python
required_ext = _find_extension(pool, "buf.validate.field")   # None when no file imports buf/validate
...
required = required_ext is not None and f.options.HasExtension(required_ext) \
           and f.options.Extensions[required_ext].required
```

and add one branch in front of the `optional` branch:

| Field | Result | Error (new) |
|---|---|---|
| `optional` + `required` | `name: type`, no default (a required dataclass field) | — |
| `optional` + `required` + `default_*` or `nullable` | refused | `x: required contradicts a default or nullable` |
| plain + `required` | refused | `x: a required field must be optional (explicit presence); see docs/decisions/required-fields-explicit-presence.md` |
| `repeated` + `required` | refused | `x: a repeated field is always a tuple, empty by default` (the current message, extended to `required`) |

The "plain + `required`" refusal goes slightly beyond the definition of done. It enforces the
decision's "always `optional` **and** `required`, never one without the other" (variant B is
rejected there). Drop it if you'd rather keep 5.3c minimal.

Nothing else changes. A range rule alone doesn't make a field required, and the "required field
after an optional one" check works on the result (`default is None`), so it covers the new branch
without edits.

**Module docstring.** Add the line
`optional scalar + (buf.validate.field).required  ->  name: type  (required)`.

### 4. Other `protoc` calls on `simulation_input.proto`

| Call site | Change | Check |
|---|---|---|
| `docs/experiments/protobuf-languages/python/_setup.py` | Pass `--descriptor_set_in=…/backend/proto/buf_validate.binpb` on the **first** call too (it compiles `simulation_input.proto` without it today). Point both calls at the moved file | `pytest docs/experiments/protobuf-languages/python`: 27 pass |
| `docs/experiments/protobuf-languages/typescript/package.json` `generate` | `buf generate ../../../../backend/proto` can't resolve the import without a `buf.yaml`. Use `protoc` with `--descriptor_set_in`, as `generate:rules` already does, with `rewrite_imports=./buf/validate/*_pb.js:@bufbuild/protovalidate/gen`. Drop `buf.gen.yaml` if nothing else uses it | `npm run generate && npm test`: 8 pass; `src/gen/sincero/simulation_input_pb.ts` now has `listPrice?: number` |
| `docs/experiments/protobuf-languages/connect/generate.sh` | Add `--descriptor_set_in`. If the generated `simulation_input_pb.py` imports a `buf.validate` module that the protobuf-py runtime can't find, add `buf/validate/validate.proto` to the file list | `./generate.sh` runs; the server starts |
| `generate:rules` (TypeScript) | Point it at the moved descriptor set | Same `npm test` |

The TypeScript type change (`listPrice?: number | undefined`) can break `experiment.ts`/`test.ts`
type checks where they read the field. Fix them with a presence check, which is what the decision
expects of client code.

### 5. Dependencies

Add `protovalidate>=2.1` to `backend/requirements-dev.txt`. The runtime test needs it, and today it
works only because the package happens to be installed in `.venv`. It moves to `requirements.txt`
when the server validates requests (5.5/5.6).

## Tests

`tests/test_gen_dto.py`: the 19 existing tests stay **unedited**, per the definition of done. Add:

1. `test_required_presence_maps_to_a_required_field`: on a throw-away proto (the `render_proto`
   helper, with `import "buf/validate/validate.proto";` in its preamble),
   `optional double x … (buf.validate.field).required = true` renders as `x: float` with no default.
2. Parametrized refusals, added to the existing table or a new one: `required` + `default_number`,
   `required` + `nullable`, plain + `required`, `repeated` + `required`, each with its message.
3. `test_range_rule_alone_does_not_make_a_field_required`: `optional` + `double.gt` and no default
   is still refused as `optional, but neither a default nor nullable`.
4. `test_list_price_and_months_remaining_have_explicit_presence`: on the real file, both fields have
   `proto3_optional` and `required`.

`test_defaults_and_nullability_come_from_the_proto` and `test_generated_module_is_up_to_date` already
pin "the generated DTO still has no default on a required field" and "`make dto` leaves no diff".

New `tests/test_input_presence.py` (needs `protovalidate`). Build the message from
`gen_dto.compile_proto`, parse JSON with `json_format.Parse` as a Connect server would, then call
`protovalidate.validate`:

| Body | Expected violation (`field`, `rule_id`) |
|---|---|
| `{}` | `list_price` `required` **and** `months_remaining` `required` |
| `{"list_price": null, "months_remaining": 19}` | `list_price` `required` |
| `{"list_price": 440000, "months_remaining": null}` | `months_remaining` `required` |
| `{"list_price": 0, "months_remaining": 19}` | `list_price` `double.gt` (not `required`) |
| `{"list_price": 440000, "months_remaining": 0}` | `months_remaining` `int32.gte_lte` (not `required`) |
| `{"list_price": 440000, "months_remaining": 601}` | `months_remaining` `int32.gte_lte` |
| RA (`440000`, `19`, `fgts_upfront: 13000`) | none |

One test asserts that `0` and absent give **different** `rule_id`s. It is the test that fails under
variant A and pins the decision rather than the rules.

## Docs to update in the same PR

- `docs/decisions/required-fields-explicit-presence.md`: status line ("applied to
  `simulation_input.proto` in 5.3c"); "Not done yet" item 3 → done; note that item 1 is now closed by
  the rules on the real message, with the server change left to M5.
- `tasks.md` 5.3c checked, with the date and test count. It is untracked, so this is a local edit.
- `docs/experiments/protobuf-languages/README.md`, `python/README.md`, `typescript/README.md`: the
  descriptor set's new path.
- `backend/README.md`: one line on `make dto` needing `buf_validate.binpb`, if it describes `make dto`.

## Order of work

1. Move `buf_validate.binpb` to `backend/proto/`, add `backend/proto/README.md`, repoint the
   experiments. Run `make test` and the 27 Python experiment tests: they pass (no behaviour change).
2. `gen_dto.py`: `--descriptor_set_in` + compile `validate.proto`; the new tests from Tests 1–3. Run
   `make dto` (no diff) and `make test`.
3. The `.proto` change and its header. Run `make dto` (still no diff), add Tests 4 and
   `test_input_presence.py`, add `protovalidate` to `requirements-dev.txt`, then run `make test`.
4. Regenerate the TypeScript and Connect experiments; fix the TS type checks; run `npm test`.
5. Docs.

Commit by concern, roughly one per step.

## Definition of done (from tasks.md, with the checks)

| Criterion | Check |
|---|---|
| `make dto` leaves no diff | `make dto && git diff --exit-code app/models/input_fields.py` |
| `make test` passes with the existing `test_gen_dto.py` tests unedited, plus new cases | `git diff develop -- backend/tests/test_gen_dto.py` shows only additions; `make test` green |
| The generated DTO has no default on a required field | `test_defaults_and_nullability_come_from_the_proto` (existing) |
| `protovalidate` on the real `SimulationInput` refuses `{}`, `null` and zeros | `tests/test_input_presence.py` |
| Every `protoc` call resolves `buf/validate/validate.proto` | `_setup.py` (27 tests), `npm run generate && npm test` (8 tests), `generate.sh` runs |

## Risks

| Risk | Mitigation |
|---|---|
| Two copies of `buf.validate` in one Python process (the one generated by `compile_proto` and one shipped by a package) clash in the default descriptor pool | Today nothing in `backend` imports another copy; `protovalidate` 2.1 ships none (checked: no `buf.validate` module installed). If 5.5 brings one, import it instead of generating |
| The descriptor set is older than `protovalidate` 2.1 expects | The experiment already runs `protovalidate` 2.1 against this set (27 tests); keep them green |
| `json_format.Parse` treats `null` on an `optional` scalar differently from Connect's codec | The decision's evidence parses as Connect does; the `null` rows above pin it |
| The TypeScript type change ripples into experiment code | Step 4, isolated; the experiments are not part of `make test` |
