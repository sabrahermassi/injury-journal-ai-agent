---
name: pr-review
description: Review the current branch or a pull request for real defects only — logic, security, privacy of health data, LLM output handling, API contracts and tests that don't test what they claim. Explains each problem for a learner without rewriting the code. Use when asked to review changes in this repository.
---

# Review

I am learning. Explain each problem and the concept behind it. Do not rewrite my code or give full solutions unless I ask.

## What to review

- Locally: the diff of this branch against main, including uncommitted changes (`git diff main`) and new untracked files (`git status`).
- On GitHub: the pull request's diff.
- The changed files in full, plus their direct callers. Do not survey the rest of the codebase.

## CodeRabbit first

Before reviewing, read the review comments already on the pull request.

- **If CodeRabbit already reviewed** (it has comments on this PR): do not repeat anything it raised, even reworded and even if it isn't fixed yet. Report only new problems.
- **If CodeRabbit has not reviewed** (no comments from it, for example because it hit its limit): do a full review.
- Locally, with no pull request, do a full review.

## Check against

- Privacy: note text, chunks or questions never appear in logs, error messages or responses they don't belong in. `data/` and `.env` are never committed.
- Validation: every request is validated (Zod in `api/`, Pydantic in `app/`), and Python's answers are validated in the TS API.
- LLM output: treated as untrusted. Its shape is validated before use, quotes are checked against the source, and it is never run as code or SQL without checks.
- SQL: parameters only. Generated SQL is parsed and limited to one read-only SELECT.
- Concurrency: two requests at once can't lose or duplicate data.
- Tests: would they fail if the code were wrong? Models are faked, never called for real.
- AGENTS.md rules, including the per-project folder layout.

## Severity

Report only:

- **P0**: data loss, a security or privacy hole (health data leaked or logged), a crash a user can reach.
- **P1**: a real bug with a concrete failure path, or code that breaks an API contract between React, the TS API and Python.

Every finding needs a concrete scenario: the input or state that triggers it, and the wrong result. Re-read the code and confirm nothing already prevents it. Drop anything that doesn't survive.

## Ignore

Formatting, naming, import order, file layout, comments, and refactors that don't fix a bug.

## Output

One entry per finding:

**[P0|P1] file:line** — What breaks. The input that breaks it. The concept to learn. What to change, in one sentence, without code.

Keep every entry short, whether or not CodeRabbit ran.

If nothing survives, reply `No issues found.` (or `Nothing new beyond CodeRabbit's comments.` if CodeRabbit already reviewed) and stop. No summary, no praise.
