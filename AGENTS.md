# AYNA — Agent Instructions

You are a coding agent working for **one** member of a three-person team. Three agents work on this repo in parallel, so these rules exist to keep work traceable and to stop agents from overwriting each other. Read this whole file before doing anything. Talk to the user in their language (Turkish); write code, comments, commits, issues and memory in **English**.

## 1. Project

AYNA (Akıllı, Yerli, Nesne Tabanlı Arayüz Testi) is a codeless, closed-network UI test automation platform for Windows desktop apps — a licence-free alternative to the core of TestComplete. Senior capstone (Ankara University COM 4061-4062), HAVELSAN SUIT application.

- Stack: Python automation agent (pywinauto) · Electron + React client (JavaScript) · Java Spring Boot server · Neo4j (single database) · Python AI service (local LLM via Ollama / llama.cpp).
- Product knowledge: `memory-bank/project/` (brief, architecture, conventions, glossary).
- Decisions already made: `memory-bank/decisions/README.md`.
- Tasks, status, acceptance criteria: **GitHub Issues** + the "AYNA" GitHub Project. Weeks are milestones.

## 2. Team, identity and ownership

| id | Person | GitHub | Owns (primary) |
|---|---|---|---|
| `galip` | Galip Enes Doğan | @galipdg | `ai/`, `agent/ayna_agent/recognition/`, `agent/ayna_agent/heal/`, `eval/nl/` |
| `omer` | Ömerfaruk Sarıbal | @omerfaruksaribal | `server/`, `client/`, `.github/`, `docker/` |
| `hasan` | Hasan Berk Yanıkkaya | @HasanBerk18 | `agent/ayna_agent/playback/`, `agent/ayna_cli/`, `eval/` (except `eval/nl/`), `docs/` |

Shared by all three: `schemas/` (frozen contracts — changing them needs an ADR and everyone's approval), `memory-bank/project/`, `memory-bank/decisions/`.

**Identity.** At session start, find out whom you work for: read `CLAUDE.local.md` (line `ayna-user: <id>`); if it is missing, match `git config user.email` / `user.name` against the table; if still unclear, ask. Never guess. Below, `<you>` means that id.

**Stay in your lane.** Change only files your user owns or the current issue clearly requires. If another person's code or memory needs a change, do not edit it: append a request to `memory-bank/people/<them>/inbox.md` and tell your user.

## 3. Session start (before any work)

1. `git status` and `git fetch`. Never work on `main`; if you are on it, ask which issue to work on and create the branch (§6).
2. Read `memory-bank/people/<you>/active.md` and `memory-bank/people/<you>/inbox.md`.
3. Read the issue: `gh issue view <n>`. Then read `memory-bank/tasks/<n>-*.md` if it exists; create it from `memory-bank/tasks/_template.md` if the task is new.
4. Skim `memory-bank/decisions/README.md` (the index, not every ADR).
5. Tell the user in 3–5 lines what you understood, what you will do first, and any open questions. Then start.

Do **not** read the whole memory bank up front. Open other files only when the work needs them. Each top-level folder has its own `AGENTS.md` with build/test commands — read it when you work there.

## 4. Memory map — what lives where, who writes it

| Path | Holds | Who writes | How |
|---|---|---|---|
| `memory-bank/project/*` | Stable product knowledge | Anyone, after asking the user | Via PR only |
| `memory-bank/decisions/YYYY-MM-DD-slug.md` | One architectural/process decision (ADR) | Anyone | New file + one line in `decisions/README.md`. Never edit an accepted ADR; supersede it with a new one |
| `memory-bank/tasks/<issue>-<slug>.md` | Working notes for one issue: approach, small decisions, status, next step, handoff | Issue assignee only | Overwrite sections freely |
| `memory-bank/people/<you>/active.md` | Your current focus, exact next step, open questions | Only you | Overwrite |
| `memory-bank/people/<you>/journal.md` | One entry per session | Only you | Append only |
| `memory-bank/people/<anyone>/inbox.md` | Requests and notes for that person | Anyone | Append only; the owner deletes handled items |
| `memory-bank/learnings.md` | Gotchas and discoveries useful to everyone | Anyone | Append only |

- **GitHub Issues are the source of truth** for scope, status and acceptance criteria. Link the issue; never copy its criteria into memory.
- **Code wins over memory.** If they disagree, trust the code, tell the user, and fix the memory in the same branch.
- Append-only files use `merge=union` (see `.gitattributes`): always add new entries at the end, never reorder or rewrite old ones.

## 5. When and how to update memory

Update at checkpoints, not after every step:
- a decision is made → task note (small) or new ADR (affects others or is hard to reverse);
- a meaningful unit is committed → task note "Status / Next step";
- you hit a non-obvious problem → `learnings.md`;
- something concerns a teammate → their `inbox.md`;
- session ends → `active.md` + one `journal.md` entry (§10).

Commit memory changes **together with** the code they describe. Write short, dated (`YYYY-MM-DD`) bullets. Record *why*, not what the code already says. Link issues (`#21`), paths and commits. Delete what has gone stale. Never write secrets.

## 6. Git workflow

- Branch per issue: `<you>/<issue>-<short-slug>` (e.g. `galip/21-element-from-point`). Never commit on `main`.
- Commit after each small, **working** unit (its tests pass). Conventional Commits with the issue number: `feat(agent): add elementFromPoint (#21)`. Types: `feat fix refactor test docs chore build ci`.
- Before committing, run the tests and linters of the module you touched (see its `AGENTS.md`). If you must commit something broken, ask first and prefix the subject with `wip:`.
- Push only your own branch. Open the PR with the template; the body includes `Closes #<n>`.
- **Never**: push to `main`, force-push, merge a PR, rewrite pushed history, or delete branches you did not create. A hook blocks the worst of these; do not try to work around it.
- Never commit secrets, `.env`, large binaries, model weights or generated build output.

## 7. Ask the user before you

- add, remove or upgrade a dependency;
- change anything in `schemas/`, an API contract, the Neo4j graph schema or a migration;
- touch files owned by another person (§2);
- delete or rename files outside the issue's scope;
- change this file, any `AGENTS.md`, the memory structure, CI, hooks or `.github/`;
- change the plan: scope, week, owner or acceptance criteria of an issue;
- push, open a PR, or run anything that leaves the machine;
- do anything you cannot undo.

When in doubt, ask. If the user is unavailable, take the safest reasonable option and write the assumption in the task note.

## 8. Speak up

- If the plan, the issue, its acceptance criteria, existing code or memory looks wrong, risky or contradictory, **say so before working around it** — briefly, with a suggested fix.
- Do not fix out-of-scope problems silently. Note them in the task note under "Open issues" and suggest a new GitHub issue.
- If you think the user's request is a bad idea, say why in one or two sentences, then follow their decision.

## 9. Quality and honesty

- Never say something works or tests pass unless you ran it in this session. Say what you could not verify.
- An issue is done only when every acceptance criterion in the issue is met, tests and CI pass, memory is updated and a PR exists.
- Product code must run on a closed network: no runtime calls to external services, CDNs or telemetry.
- Do not hand-edit generated files (e.g. `docs/api/openapi.yaml`).
- Keep the diff inside the issue's scope. Prefer simple, readable code over clever code.

## 10. Session end and handoff

Hand off when: the issue is done; you switch to another issue; the session has grown long (many files read, a long conversation, context use above ~60% in `/context`) or your answers get less precise; or before a long break.

1. Update the task note (status, exact next step, open issues) and `people/<you>/active.md`.
2. Append one entry to `people/<you>/journal.md` (date, issue, what changed, next step).
3. Commit (and push only if the user agrees).
4. Tell the user it is a good moment for a fresh session and give a ready prompt of at most three lines, for example:

```
Continue #21 (element under cursor) as galip. Follow the AGENTS.md session-start steps.
Next step: add DPI-scaling test at 150%.
```

The prompt stays short because the state lives in memory, not in the prompt.
