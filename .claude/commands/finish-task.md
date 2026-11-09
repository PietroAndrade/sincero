---
description: Test, push, open and squash-merge the PR for the current feat/* branch, then start the next branch from develop
---

Finish the current task on branch `$(git branch --show-current)`:

1. Commit any pending work in small commits by concern. Leave `tasks.md` and `*brief.md` untracked.
2. From `backend/`, run `make test` with `backend/.venv/bin` on `PATH` (create the venv from `requirements-dev.txt` if missing). Stop and report if anything fails.
3. `git push -u origin <branch>` (the `.githooks/pre-push` hook reruns the tests), then `gh pr create --base develop`. The PR body ends with the Claude Code attribution line.
4. `gh pr merge <n> --squash`. Merge only through the GitHub PR, never squash locally, never push to `develop`. If the base branch policy blocks the merge (`REVIEW_REQUIRED`: the repository has a single owner, who is the author), retry with `gh pr merge <n> --squash --admin`; the owner authorised this. Any other failure (conflicts, failing checks) is not covered: stop and report.
5. `git checkout develop && git pull --ff-only origin develop`.
6. Create the next branch from `develop`, `feat/<topic>`, named after the next unchecked task in `tasks.md`.

Report the PR URL and the new branch name.
