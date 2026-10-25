# Inbox — Galip Enes Doğan (`galip`)

Anyone may append; only galip removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from omer · #2 · Please protect `main` (PR + 1 approving review, no direct pushes). Only the repo owner can: omer has no admin, and GitHub refuses protection/rulesets on a private repo of a free personal account. Enable GitHub Pro via the Student Developer Pack (or move the repo to an org / make it public), then set the rule in Settings → Branches. Details: `memory-bank/tasks/2-monorepo-setup.md`.
- 2026-10-25 · from omer · #3 · CI needs a trivial test, so the `omer/3-ci-skeleton` PR adds a minimal `ai/pyproject.toml` (ruff~=0.17.2 + pytest as `[dev]`), an empty `ai/ayna_ai/` package and `ai/tests/test_smoke.py`, plus the same for `agent/` (`ayna_agent`). Please review (you are a CODEOWNER) and change freely. `ai/spikes/` is excluded from ruff because `llm_smoke.py` fails ruff 0.17 (PLW1510 ×2 + formatting); keep the exclusion or clean the script up. When you have time, fill the "Commands" section in `ai/AGENTS.md` and `agent/AGENTS.md` (`pip install -e ".[dev]"`, `ruff check .`, `ruff format --check .`, `pytest`).
