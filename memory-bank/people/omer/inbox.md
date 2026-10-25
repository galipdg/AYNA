# Inbox — Ömerfaruk Sarıbal (`omer`)

Anyone may append; only omer removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from hasan · #3 · Answering your CI notes. (1) `ayna_cli/`: I will add it to `[tool.setuptools.packages.find]` in `agent/pyproject.toml` when I start #61 (CLI runner skeleton); nothing needed from you now. (2) `eval/` CI: I would like that job, but `eval/apps/trial/` currently uses `eval/apps/trial/requirements.txt` rather than a `pyproject.toml`, which conflicts with `conventions.md` ("dependencies in `pyproject.toml`"), and its code has never been through `ruff`. That is more than a CI switch, so I think it deserves its own issue — something like "eval: pyproject + ruff + CI job" — rather than being bolted onto #3. I have noted it in `memory-bank/tasks/8-working-agreement.md` under Open issues; tell me if you would rather just add the job and let me fix the lint fallout.
