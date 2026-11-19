# Working agreement — AYNA

How the three of us work together on AYNA (Akıllı, Yerli, Nesne Tabanlı Arayüz
Testi), the senior capstone for Ankara University COM 4061–4062.

Semester 1 runs **20 Oct 2026 – 25 Jan 2027**. This document is the social
contract; the machine-readable version of most of it lives in
[`AGENTS.md`](../AGENTS.md) and
[`memory-bank/project/conventions.md`](../memory-bank/project/conventions.md).
Where this document and those files disagree, **the repo files win** and this
document gets fixed.

Issue: [#8](https://github.com/galipdg/AYNA/issues/8).

## 1. Roles and ownership

| id | Person | GitHub | Owns (primary) |
|---|---|---|---|
| `galip` | Galip Enes Doğan | @galipdg | `ai/`, `agent/ayna_agent/heal/`, `agent/ayna_agent/rpc.py`, `eval/nl/`, `docs/rs/`, `docs/report/` |
| `omer` | Ömerfaruk Sarıbal | @omerfaruksaribal | `server/`, `client/`, `.github/`, `docker/`, `docs/sdd/`, `docs/ui/` |
| `hasan` | Hasan Berk Yanıkkaya | @HasanBerk18 | `agent/ayna_agent/recognition/`, `agent/ayna_agent/playback/`, `agent/ayna_cli/`, `eval/` (except `nl/`), `docs/` (except `rs/`, `report/`, `sdd/`, `ui/`) |

Shared by all three: `schemas/` (frozen contracts — changing one needs an ADR and
everyone's approval), `memory-bank/project/`, `memory-bank/decisions/`.

This table follows ADR *windows-work-to-hasan*: work that needs a Windows machine (UI
Automation, pilot apps, measurements on them) is hasan's, which moved
`agent/ayna_agent/recognition/` to him. The client screens stay with omer, who builds them
on macOS and checks them at the weekly Windows session (§11). The root
[`AGENTS.md`](../AGENTS.md) §2 holds the same table and is the version the agents read, so
the two must be changed together.

**Stay in your lane.** Change only what you own or what the current issue clearly
requires. If someone else's code or memory needs a change, do not edit it: append
the request to `memory-bank/people/<them>/inbox.md`.

Ownership is about *who decides and reviews*, not about who may read. Everyone
reads everything.

## 2. Rhythm

- **A week is a milestone.** Weeks start on **Tuesday**, which is also the advisor
  meeting day. Every issue belongs to exactly one week.
- **A sprint is two consecutive weekly milestones** (weeks 1–2, 3–4, and so on).
  The weekly milestones stay exactly as they are; a sprint is just the pair,
  closed with a short review of what shipped and what slipped. Gates do not line
  up with sprint boundaries — they fall in weeks 3, 7, 9, 12 and 14 — so a gate
  is reviewed on its own week regardless of where the sprint ends.
- **Gates** are the checkpoints where we stop adding and verify what exists:

| Gate | What it checks | Week | Issue |
|---|---|---|---|
| G0 | Walking skeleton demo | 3 | [#28](https://github.com/galipdg/AYNA/issues/28) |
| G1 | Design baseline review | 7 | [#56](https://github.com/galipdg/AYNA/issues/56) |
| G2 | MVP core demo | 9 | [#70](https://github.com/galipdg/AYNA/issues/70) |
| G3 | Feature freeze check | 12 | [#88](https://github.com/galipdg/AYNA/issues/88) |
| G4 | End-of-semester demo | 14 | [#96](https://github.com/galipdg/AYNA/issues/96) |

- **Fixed deadlines** (these outrank milestone order if the calendar gets tight):
  Requirements Specification **23 Nov 2026**, Software Design Document
  **7 Dec 2026**, semester report and evaluation set **Week 14**.

## 3. Communication

- **Channel:** a **WhatsApp group** for day-to-day coordination — "I am blocked",
  "PR ready for review", "can you look at this". Chat is easy to lose, so
  anything that is a *decision* is written the same day into an ADR or the
  relevant issue, and the group only points at it.
- **Tuesday meeting:** the three of us meet **immediately after the advisor
  meeting**, the same day. Standing agenda: what each of us closed last week,
  what is blocked and on whom, decisions needed this week, next week's issues.
  Whoever runs the meeting writes decisions straight into an ADR or the relevant
  issue — not into chat, where they get lost.
- **Asynchronous, in order of preference:** the issue itself → the PR → the
  owner's `memory-bank/people/<id>/inbox.md`. Anything that affects a teammate's
  work goes in writing, not only in the meeting.
- **Language:** we talk Turkish; everything written into the repo — code,
  comments, commits, issues, PRs, memory — is **English**.
- **Response expectation:** a review request or an inbox item should get an
  answer by the next Tuesday meeting at the latest. If something blocks you, say
  so the same day rather than waiting.
- **Advisor summary:** hasan writes it and sends it by **email** after the
  Tuesday meeting. Everyone supplies their own part from that week's
  `journal.md` entry, so nobody has to summarise somebody else's work.

## 4. How we use GitHub

**GitHub Issues are the single source of truth** for scope, status and acceptance
criteria. We never copy acceptance criteria into other documents; we link the
issue.

- **Milestones** = weeks. **Labels**: `area:*` (which module), `owner:*` (who),
  `gate`, `decision`, `course-deadline`, `needs-windows-test`.
- **Project board** ("AYNA", `galipdg` project 1): `Todo → In progress → Done`.
  You move your issue to *In progress* when you actually start it; closing the
  issue moves it to *Done* automatically. Commands are in `conventions.md`.
- An issue body carries **Description**, **Expected output**, **Acceptance
  criteria** and **Depends on**. Do not start an issue whose dependencies are
  still open; if you must, say why in the task note.
- **Changing an issue's scope, week, owner or acceptance criteria is a team
  decision**, taken in the meeting or in the issue thread — not silently while
  implementing it.

## 5. Branches, commits, pull requests

- One issue → one branch → one PR. Branch name: `<id>/<issue>-<short-slug>`
  (e.g. `hasan/8-working-agreement`). **Never commit on `main`.**
- Commit after each small unit that **works** (its tests pass). Conventional
  Commits with the issue number: `feat(agent): add elementFromPoint (#21)`.
  Types: `feat fix refactor test docs chore build ci`. Scopes:
  `agent ai client server schemas eval docs memory ci build`.
- Before pushing: `git fetch origin`; if `origin/main` moved, **merge it into your
  branch** (never rebase, never force-push) and rerun the tests, so the PR has no
  conflicts.
- Append-only memory files (`learnings.md`, `inbox.md`, `journal.md`) use
  `merge=union`: always append at the end, never reorder. A local `git merge`
  resolves them automatically — do not resolve those conflicts in GitHub's web
  editor, which does not apply the union rule.
- **Never:** push to `main`, force-push, merge your own PR, rewrite pushed
  history, or delete a branch you did not create. Never commit secrets, `.env`,
  large binaries, model weights or build output.

## 6. Definition of Done

A change is done when every box in
[`.github/pull_request_template.md`](../.github/pull_request_template.md) is
ticked honestly:

- [ ] Tests for the change pass locally and in CI
- [ ] Linters pass
- [ ] User-facing docs updated (module README / `AGENTS.md`, guides, API docs) if behaviour changed
- [ ] Task note `memory-bank/tasks/<issue>-*.md` updated (status, outcome)
- [ ] ADR added if a decision affects others or is hard to reverse
- [ ] No secrets, `.env`, large binaries or generated files committed

An **issue** is done only when every acceptance criterion in the issue is met, CI
is green, memory is updated and the PR is merged. A box you cannot tick honestly
stays unticked, with one line saying why — half-true checklists cost more than
open items.

## 7. Review and merge

- **One approving review from someone other than the author**, then the author's
  human merges. Nobody merges their own PR unreviewed, and an agent never merges.
- Review for: does it meet the acceptance criteria, is it inside the issue's
  scope, does it stay in the author's lane, are the claims about testing true.
- If a PR touches `schemas/`, the Neo4j model or an API contract, **all three**
  approve and there is an ADR.
- Reviews are about the change, not the person. Disagreement goes in the PR
  thread with a suggested alternative, not in chat.

## 8. Decisions

- One decision → one ADR in `memory-bank/decisions/YYYY-MM-DD-slug.md`, plus one
  line in [`decisions/README.md`](../memory-bank/decisions/README.md).
- An accepted ADR is **never edited**. If it turns out wrong, write a new one that
  supersedes it and mark the old line `Superseded by …`.
- Small decisions local to one issue go in that issue's task note instead.
- `decision`-labelled issues (D1, D2, …) are decisions we scheduled in advance.

## 9. Memory bank

`memory-bank/` is the project's shared memory. Who writes what:

| Path | Holds | Who writes |
|---|---|---|
| `project/*` | Stable product knowledge | anyone, via PR |
| `decisions/*` | One ADR per decision | anyone |
| `tasks/<issue>-*.md` | Working notes for one issue | that issue's assignee |
| `people/<id>/active.md` | That person's current focus and next step | only that person |
| `people/<id>/journal.md` | One entry per session (append-only) | only that person |
| `people/<id>/inbox.md` | Requests for that person (append-only) | anyone; owner deletes handled items |
| `learnings.md` | Gotchas useful to everyone (append-only) | anyone |

Two rules that matter: memory changes are committed **together with** the code
they describe, and **code wins over memory** — if they disagree, trust the code
and fix the memory in the same branch.

## 10. We each work with a coding agent

Each of us drives a Claude Code agent on this repo, in parallel.
[`AGENTS.md`](../AGENTS.md) is the contract those agents follow: session-start
steps, ownership, git rules, and the list of things an agent must ask its human
before doing (dependencies, `schemas/`, another person's files, CI, hooks,
pushing, anything irreversible).

What this means for us as a team:

- The agent works for **one** of us and identifies itself from `CLAUDE.local.md`
  (`ayna-user: <id>`). It never edits another person's files.
- An agent may **not** merge a PR, push to `main`, or decide a plan change.
- An agent must not claim something works unless it ran it in that session.
  "I could not verify this" is an acceptable answer; a false green is not.
- Changing `AGENTS.md`, any module `AGENTS.md`, the memory structure, CI or
  `.github/` is a team decision like any other.

## 11. Weekly Windows test session

Much of AYNA can only be judged on Windows: the Spy overlay, hotkeys, DPI
scaling, real pilot apps. galip works on macOS, so Windows-only work
(`@pytest.mark.windows`, UI Automation, pilot apps) is verified **once a week on
hasan's Windows machine with both present**
([ADR](../memory-bank/decisions/2026-10-25-weekly-windows-test-session.md)).

- Code that is ready but needs Windows: post the manual check and the exact
  commands as an issue comment, add the label `needs-windows-test`, and keep
  working on what can be verified elsewhere.
- At the session: `gh issue list --label needs-windows-test`, run each one with
  its owner, post the result as an issue comment. Pass → remove the label.
  Fail → the label stays and the failure (issue, step, log lines, screenshot)
  goes to the owner's `inbox.md`.
- A manual check that keeps coming back should become an automated
  `@pytest.mark.windows` test, or a checklist in `docs/manual-checks/`.

## 12. Quality bar

- **Closed network:** product code makes no runtime calls to external services,
  CDNs or telemetry. If a feature needs the internet, it is not a feature.
- **CI** runs on every PR: `server`, `client`, `agent`, `ai`
  ([`ci.yml`](../.github/workflows/ci.yml)). `eval/` has no job yet; until it
  does, running and reporting its tests is the author's responsibility.
- Python: `ruff check`, `ruff format`, `pytest`; Windows-only tests marked
  `@pytest.mark.windows`. Java: `./mvnw -B verify`. See `conventions.md`.
- Generated files (e.g. `docs/api/openapi.yaml`) are never hand-edited.
- Say what you did **not** verify. An unverified claim in a PR body is worse than
  an open checkbox, because the next person builds on it.

## 13. When something goes wrong

- **Blocked on a teammate:** say it the same day in the channel and write it in
  the issue, so the next Tuesday meeting starts from a known state.
- **Found a problem outside your issue:** do not fix it silently. Note it in the
  task note under "Open issues" and propose a new GitHub issue.
- **The plan looks wrong:** say so before working around it, with a suggested
  fix. This is expected, not disloyal.
- **A gate or deadline is at risk:** raise it at least one week early; cutting
  scope is a team decision, and the earlier it is taken the cheaper it is.

## 14. Changing this agreement

Open an issue or raise it on Tuesday, then change it in a PR that all three
approve. If a change also affects how the agents behave, update
[`AGENTS.md`](../AGENTS.md) in the same PR — otherwise the agents keep following
the old rule, and the repo files win over this document by design.
