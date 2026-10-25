# Inbox — Hasan Berk Yanıkkaya (`hasan`)

Anyone may append; only hasan removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from omer · #3 · The `omer/3-ci-skeleton` PR adds a minimal `agent/pyproject.toml`, an empty `agent/ayna_agent/` package and `agent/tests/test_smoke.py` so the CI agent job (windows-latest: ruff + pytest) has something to run. `ayna_cli/` is not created; add it to `[tool.setuptools.packages.find]` when you start it. Please review. `eval/` has no CI job yet; once it has a `pyproject.toml` I can add one (or open an issue).
