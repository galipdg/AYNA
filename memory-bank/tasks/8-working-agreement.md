# #8 Kick-off notes and working agreement

- Issue: https://github.com/galipdg/AYNA/issues/8
- Owner: hasan · Branch: `hasan/8-working-agreement`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
`docs/working-agreement.md` is written by **deriving** the rules that already
exist in the repo rather than inventing new ones, so the document and the repo
cannot drift apart:

| Section | Derived from |
|---|---|
| Team, ownership | `AGENTS.md` §2 |
| Rhythm, gates, deadlines | `memory-bank/project/brief.md` (calendar), `docs/AGENTS.md` |
| Board usage | `memory-bank/project/conventions.md` (Project board) |
| Branch/commit/PR rules | `AGENTS.md` §6, `conventions.md` (Commits and PRs) |
| Definition of Done | `.github/pull_request_template.md` |
| Decisions | `memory-bank/decisions/README.md` |
| Memory bank | `AGENTS.md` §4 |
| Windows test session | ADR 2026-10-25-weekly-windows-test-session |
| CI | `.github/workflows/ci.yml` |

Where the repo is genuinely silent, the document carries an explicit **TBD**
instead of a guess: the communication channel, the Tuesday meeting time, how the
weekly milestones map onto the "2-week sprints" the issue asks for, and how the
advisor summary is delivered. Asked the user.

## Decisions (small, local to this task)
- 2026-10-25 — The agreement links to `AGENTS.md`, `conventions.md` and the PR
  template instead of copying them, except for the Definition of Done, which is
  quoted in full because the issue's acceptance criterion names it explicitly.
- 2026-10-25 — The user's four answers: WhatsApp group for day-to-day chat; the
  team meets straight after the Tuesday advisor meeting; **a sprint = two
  consecutive weekly milestones** (milestones stay weekly, so the 15 existing
  milestones are untouched and #8's "2-week sprints" is still satisfied); hasan
  writes the advisor summary by email from everyone's journal entries.
- 2026-10-25 — Gates (weeks 3, 7, 9, 12, 14) deliberately do **not** align with
  sprint boundaries, and the document says so instead of pretending they do.

## Status
- [x] Branch created from the updated `main`, board status set to In progress
- [x] `docs/working-agreement.md` written (15 sections, all local links verified)
- [x] Inbox tidied: omer's #2 request is satisfied by the merged PR #116, so it was
      removed; his #3 notes were answered in his inbox
- [x] All four TBDs answered by the user and written into the document; the
      "Open points" section is gone, so the agreement has no placeholders left
- [ ] PR opened; all three members approve it
- [ ] Advisor received the summary (user's action, cannot be done by the agent)
- Next step: push and open the PR (needs the user's OK), then ask galip and omer to review.

## Manual checks
Not applicable — a document, no runtime behaviour.

## Open issues
- 2026-10-25 — Two acceptance criteria of #8 need other people: "all three members
  approved it in a PR" and "advisor received the summary". The issue cannot be
  closed in this session no matter how good the document is.
- 2026-10-25 — `eval/` has no CI job and no `pyproject.toml`, while
  `conventions.md` requires `pyproject.toml` + `ruff` for every Python module.
  `eval/apps/trial/` currently uses `requirements.txt` (user's choice in #9) and
  has never been linted, so nothing guards its 7 pure tests. omer offered to add
  the job once eval has a `pyproject.toml` (his note in hasan's inbox, #3).
  Suggest a new issue; out of scope here.

## Handoff
—

## Outcome (fill when the issue closes)
