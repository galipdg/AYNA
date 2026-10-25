# Inbox — Hasan Berk Yanıkkaya (`hasan`)

Anyone may append; only hasan removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from omer · #2 · Acceptance criterion "all three members cloned the repo and merged one test PR" still needs you: (1) clone `galipdg/AYNA`, copy `CLAUDE.local.md.example` to `CLAUDE.local.md` with `ayna-user: hasan`; (2) on a branch `hasan/2-test-pr`, make one small real change in your area (e.g. expand `docs/README.md` or `eval/README.md`), open a PR with the template and `Refs #2` (not `Closes`), get one approval and merge it; (3) please review omer's #2 PR. Tell omer when done so #2 can close.
- 2026-10-25 · from omer · #3 · The `omer/3-ci-skeleton` PR adds a minimal `agent/pyproject.toml`, an empty `agent/ayna_agent/` package and `agent/tests/test_smoke.py` so the CI agent job (windows-latest: ruff + pytest) has something to run. `ayna_cli/` is not created; add it to `[tool.setuptools.packages.find]` when you start it. Please review. `eval/` has no CI job yet; once it has a `pyproject.toml` I can add one (or open an issue).
