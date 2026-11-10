# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SINCERO: a cost simulator for off-plan apartment purchases in Brazil (INCC correction, construction interest, closing costs, SAC/PRICE financing, the "Caixa trigger" credit gap). The root `README.md` has the full business-rule table; update it and `README.pt-br.md` together.

**The Python engine is retired; the TypeScript engine is in.** The Python engine, the protobuf contract and the Connect service were retired on 2026-11-09 and live on the branch `legacy/python-engine` and the tag `python-engine-final`. The replacement is a TypeScript engine that runs in the browser (`docs/plan/typescript-port.md`). Phases P1 (engine package + golden master), P2 (cucumber-js) and P3 (Node CLI) are done; P4 (the web app) is next. `ROADMAP.md` and `docs/plan/backlog.md` hold the status.

Read the retired code with `git show python-engine-final:backend/app/models/simulator.py`, or restore a part with `git checkout python-engine-final -- backend/proto`. A full checkout of the old backend lives in `legacy/backend/` (git-ignored through `.git/info/exclude`; recreate it with `mkdir -p legacy && git archive legacy/python-engine backend | tar -x -C legacy`), which the experiment's harness reads (`SINCERO_PYTHON_BACKEND` overrides it).

## What is here

- `engine/` (`@sincero/engine`): the calculation engine in TypeScript, no I/O. `engine/golden/` is the golden master built from the Python engine (bit-exact on Node ≥ 24); update it only through `npm run golden:update`.
- `features/` (`@sincero/features`): the business specification in Gherkin (English) run on cucumber-js against the engine. `features/pt_br/` is a Portuguese translation kept as documentation only; keep it in sync by hand when you change a scenario. Step vocabulary: `features/README.md`.
- `cli/` (`@sincero/cli`): `npx sincero`, same flags and same text as the old `cli.py`.
- `docs/`: decisions, plans, the API contract (superseded) and the experiments. `docs/experiments/browser-engine` is the proof of concept; its Python engines (`--engine pyodide|brython|cpython`) need `legacy/backend`.
- `npm ci && npm test` (Node ≥ 24, `.nvmrc`): typecheck plus every workspace's tests. `.githooks/pre-push` runs it; `npm ci` enables the hooks (or `git config core.hooksPath .githooks`).
- `/finish-task` (`.claude/commands/finish-task.md`): test, push, PR, squash-merge on GitHub, then a new branch from `develop`.

## Rules that survive the port

Domain rules that span several files (details in the root README table):
- Month 0 is signing, months 1..N are construction, N is key handover, and bank installments start at N+1.
- Annual rates become monthly by compounding, `(1+r)^(1/12)-1`, never by division.
- Balloon amounts are **derived** from the remaining down payment and the installment; they are never an input.
- Cash or FGTS at signing reduces the developer installment first. Only the excess reduces the financed balance.
- Bit-exactness against CPython needs Node ≥ 24 (Node 22's `**` differs in the last bit); for users it is the business promise, every figure to the cent.
