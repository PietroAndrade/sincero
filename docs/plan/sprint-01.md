# Sprint 1

Status: plan, 2026-11-04. Backlog: [backlog.md](backlog.md). Length: **3 days**. Team: one developer
working with coding agents.

## Sprint goal

> By the end of this sprint, the maintainer will be able to trust that the real simulation input
> refuses an absent `list_price` or `months_remaining` before the model runs, telling "absent" from
> "zero", and the two answered decisions are on record.

It closes the last open item of the contract work (5.3) and unblocks 5.4, the first service task.

## Capacity

| Step | Value |
|---|---|
| Weekly availability | ~20 h |
| Per day (5 working days) | ~4 h |
| Sprint (3 days) | 12 h |
| Time off and other commitments | **−3 h (assumed: one session; replace with the real figure)** |
| Available | 9 h |
| Focus factor 0.7 | **6.3 focus hours** |
| Points (no history: assumed 1 pt ≈ 1.25 focus h) | **~5 pts** |
| Commit to 85% | **~4 pts** |

The point-to-hour ratio is a guess. This sprint measures it: record the hours actually spent on each
item in the review.

## Selected items

| # | Item | Pts | Acceptance |
|---|---|---|---|
| 0 | Close the current branch: commit `feat/accept-connect-api-decision` (docs, `docs/plan/`, ROADMAP, tasks) and run `/finish-task` | — | Merged into `develop`; new `feat/*` branch from `develop`; `make test` green |
| 1 | **5.3c** Presence rule on the real input | 3 | Definition of done in `tasks.md`: `make dto` leaves no diff; `make test` passes with `tests/test_gen_dto.py` cases unedited plus new ones; no default on a required field; `protovalidate` refuses `{}`, `null` and zeros |
| 11 | **5.17** Record the CORS decision: public domain + localhost | 1 | `docs/decisions/` record with the reason; `tasks.md` 5.17 checked |
| | **Total** | **4** | |

Item 0 is housekeeping carried over from the last session's handoff, not pointed, and goes first:
the plan documents live only in the working tree today.

## Stretch (only if the committed items are done)

| # | Item | Pts | Why it fits |
|---|---|---|---|
| 15 | **6.12** Record the language decision (PT + EN) | 1 | Answered already; writing only |
| 16 | **D1** Disclaimer wording, both languages | 1 | Needs your approval of a draft; no code |
| 5 | **5.7** Simulation store | 3 | Depends on nothing; can start in parallel with 5.4 next sprint |

## Dependencies

- 5.3c depends on nothing open. 5.4 (next sprint) depends on 5.3c.
- 5.17 and 6.12 depend on nothing; they only need writing up.
- Item 0 has to come first so the new branch starts from a `develop` that has the plan documents.

## Risks

| Risk | Mitigation |
|---|---|
| Every `protoc` call must resolve `buf/validate/validate.proto` (generator, experiments' `_setup.py`, `buf generate`, `generate.sh`); one missed call breaks `make dto` or the experiments | List the four calls before changing anything; run each after the change |
| `tools/gen_dto.py` today demands a default or `nullable` for every `optional`, so the rule change can ripple into its tests | The done criterion forbids editing existing `test_gen_dto.py` cases: add cases, don't change them |
| In the last session you said you'd run the protobuf part yourself | Decide at sprint start: you run 5.3c and I prepare and review, or I do it |
| Capacity guessed (time off, point ratio) | 4 pts is small; the stretch items absorb any slack |

## Flags from refinement

- All selected items have estimates and acceptance criteria.
- Missing for later sprints: E2 stories need refinement before 6.1 (backlog health notes), and D1 needs
  a draft to approve.

## Review checklist (end of day 3)

- [ ] Sprint goal met: `protovalidate` on the real `SimulationInput` refuses `{}`, `null` and zeros.
- [ ] Hours spent per item recorded, to set the point ratio for sprint 2.
- [ ] Unfinished items returned to the top of the backlog.
