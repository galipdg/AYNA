# #3 CI pipeline skeleton (4 jobs)

- Issue: https://github.com/galipdg/AYNA/issues/3
- Owner: omer · Branch: `omer/3-ci-skeleton`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
One workflow, `.github/workflows/ci.yml`, on every PR and on push to `main`, four parallel jobs:
- `server` — ubuntu, Temurin 21, `./mvnw -B verify` (Testcontainers uses the runner's Docker; this is also #4's "integration test in CI").
- `client` — ubuntu, Node 22, `npm ci` / `npm run lint` / `npm run build`; every step guarded by `hashFiles('client/package.json')` until #5 adds the skeleton.
- `agent` — windows-latest, Python 3.11, `ruff check`, `ruff format --check`, `pytest`.
- `ai` — ubuntu, same Python steps.

## Decisions (small, local to this task)
- 2026-10-25 — omer writes the minimal `agent/` and `ai/` scaffolds (`pyproject.toml`, empty `ayna_agent` / `ayna_ai` package, one smoke test) because CI needs a trivial test and neither package existed; galip + hasan review via CODEOWNERS and inbox. Chosen by omer over waiting for them.
- 2026-10-25 — Client job is guarded instead of waiting for #5; #3 closes only after the client job has run for real and is green.
- 2026-10-25 — `ruff~=0.17.2` pinned: ruff's default rule set grows between releases, so an unpinned ruff could turn CI red with no code change.
- 2026-10-25 — `ai/spikes/` excluded from ruff: galip's #7 spike was written without a linter and fails ruff 0.17 (2 × PLW1510, formatting). Not touched; galip decides whether to clean it up or keep the exclusion.
- 2026-10-25 — Dev tools as `[project.optional-dependencies] dev` (`pip install -e ".[dev]"`) so plain pip on the runner works; no uv needed in CI.

## Status
- [x] Workflow + agent/ai scaffolds written
- [x] Local run: agent and ai `ruff check` / `ruff format --check` / `pytest` green (1 test each, Python 3.11); server `./mvnw -B verify` green (2 tests incl. Testcontainers)
- [ ] First CI run on the PR: all four jobs green (agent on Windows)
- [ ] Client job real after #5
- Next step: ask omer to push and open the PR; check the Actions run, then close #4 with the run link.

## Manual checks
—

## Open issues
- `agent/AGENTS.md` and `ai/AGENTS.md` "Commands" are still empty; owners should fill them (asked via inbox). Not changed here (§7: AGENTS.md changes need asking + other owners).
- `eval/` (hasan, PR #116) has pytest tests but no CI job; suggest a follow-up issue for an `eval` job once it has a `pyproject.toml`.
- Windows-hosted runners do have a desktop session, but `@pytest.mark.windows` UI tests are not split out yet; decide when the first real UIA test lands (#21 / #25).

## Handoff
—

## Outcome (fill when the issue closes)
