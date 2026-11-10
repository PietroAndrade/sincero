# The golden master

The retired Python engine's answers, frozen, so that it stays the oracle after it has left the
repository (plan item P1.3, [typescript-port.md](../../docs/plan/typescript-port.md)).
`engine/test/golden.test.ts` asks the TypeScript engine the same questions and requires the same
answers **to the bit**: every number of every payload (schedules included), every key, every label,
every rejection message.

| File | What |
|---|---|
| `corpus.json` | 456 questions, one per line: `simulate`, `compare`, `cash_ladder` or `what_if`, with the input |
| `expected.json` | The Python engine's answer to each, by `id`: the outcome (`ok`, `rejected`, `invalid_shape`), the rejection message verbatim, and a SHA-256 over the exact bits of the reply. Also 400 `**` probes (see below) |
| `tools/from_python.py` | The script that wrote both, once, from the retired engine |
| `tools/update.ts` | `npm run golden:update [-- --dry-run]`: rewrites the answers from the TypeScript engine after an intended change ([protocol](../README.md#changing-the-figures)) |

## The corpus

| Source | Cases | What |
|---|---|---|
| `behave` | 55 | Every call the 54 scenarios make, recorded while behave ran the retired engine (54/54) |
| `reference` | 11 | The CLI's five reference properties (SO, F, SV, F4, RA): simulated, cash-laddered, compared |
| `random` | 363 | Seeded inputs over the whole input space: defaults, nulls, balloons, zero rates, long terms, half-cent ties, and one broken rule in ~1 case in 8 (every rule at least once) |
| `targeted` | 27 | What the random cases miss, each with a `note`: repeated and colliding cash-ladder amounts, `-0.0`, what-ifs, ties in messages up to 2^50, amounts from 1e21 up; from #450 on, the cash ladder's amount rules (P1.6) |

The first 429 cases are those of the [browser-engine experiment](../../docs/experiments/browser-engine/)
(same code, same seed). The `targeted` cases were added for P1.3. Two of them found places where the
experiment's port differed from Python and its corpus did not notice: a cash ladder with a repeated
amount (Python's variations are a dict: one row per label, not one per amount) and a half-cent tie
from 2^49 up in a message. Both are fixed in `engine/src`.

**Where the answers are no longer Python's:** P1.6 (the cash ladder's amount rules) changed five
answers on purpose, through `golden:update`: #429–#431 (repeated, colliding and unsorted amounts,
which Python accepted) and #432–#433 (a negative amount and one above the list price, which Python
refused with the model's upfront message). It also added #450–#455. Every other answer is still
the retired engine's, to the bit.

## The digest

`SHA-256` over a canonical encoding of the reply `{ok: true, value}` or
`{ok: false, kind: "rejected", error}`: numbers as IEEE-754 doubles (so `1` and `1.0` are the same,
and `-0.0` is folded into `0.0`), object keys sorted. The two implementations are
`feed()` in `tools/from_python.py` and `engine/test/digest.ts`. A reply with `undefined` in it
is an error, because JSON would drop the key. `invalid_shape` (an unknown or missing field) is kept
as an outcome only, because Python's text for it was CPython's own.

One 64-character digest per case stands for the ~1.8 M figures of the corpus (`expected.json` is 84 KB with the messages and the probes). The price is that a failing case says *that* it
differs, not *where*. To see where, run the case on both engines and compare the payloads: the
Python side with `git worktree add /tmp/py python-engine-final` (or `legacy/backend`).

## Node ≥ 24

The figures go through `**`, which is the JavaScript engine's and not the code's. V8 ≥ 13.6 (Node 24)
gives CPython's `pow` to the last bit. Node 22 differs in the last bit of ~10 % of powers, and so in
~60 cases, always below a cent. The `pow_probes` in `expected.json` are 400 powers of the engine's
two shapes with CPython's results. The test checks them first, so on the wrong runtime the failure
says so instead of blaming the engine. Browsers (Safari, Firefox) are to be checked to the cent,
not to the bit (P5.1).

## When the golden test fails

1. **Check the runtime first.** If the `**` test fails too, use Node 24 (`nvm use`); nothing is wrong
   with the engine.
2. **A `message` difference** is a rule or its text. The scenarios pin the messages: change the
   scenario first, or undo the change.
3. **A `different reply`** is a figure, a key, a label or a row. If the change was not meant to change
   figures (a refactor), it is a bug. `compensatedSum` and the order of the operations in `model.ts`
   are where refactors usually break bit-exactness.
4. **An intended change to the figures** (a new rule, a fixed rule) needs a scenario that describes it
   first. Then `npm run golden:update` rewrites the answers and the diff of `expected.json` is
   reviewed with the change: every changed line is a case whose answer changed. The steps are in
   [the engine's README](../README.md#changing-the-figures).

## Regenerating from Python

Only to fix the oracle itself, never to make a TypeScript change pass. The decision record says a fix
to the retired engine is made on `legacy/python-engine`, and the golden master is regenerated from
there:

```bash
python3 -m venv /tmp/oracle && /tmp/oracle/bin/pip install behave   # CPython >= 3.12
/tmp/oracle/bin/python engine/golden/tools/from_python.py                       # reads legacy/backend
/tmp/oracle/bin/python engine/golden/tools/from_python.py --backend /tmp/py/backend   # or a worktree of the tag
```

The script refuses to write anything if behave fails on the retired engine. It rewrites both files
whole. Once `golden:update` has recorded an intended change, the Python engine no longer gives every
expected answer, and regenerating from it would undo that change: after that, fix the oracle on
`legacy/python-engine` and carry the fix over by hand.
