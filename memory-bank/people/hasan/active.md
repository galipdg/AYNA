# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01 (fourth session of the day: omer's #179 review, D1 accepted)
- Current issue: **#21 / PR #169** (D1 pilot-apps ADR). Every acceptance criterion is met, all six
  review points are pushed, `origin/main` merged, no conflict, and the ADR is now **`Accepted`**
  (7dd2d64). Nothing is left to write: the PR waits only on galip's and omer's **Approve click**,
  which branch protection needs. Chased with a point-by-point comment on 2026-11-01.
- My open PRs, in merge order:
  1. **#169** `hasan/21-pilot-apps-adr` — `Closes #21`. Merges **first**: #170 is stacked on it,
     and the ADR cites `eval/spikes/uia-walk-cost.md`, which only reaches `main` with #170.
  2. **#170** `hasan/161-winforms-walk` — `Closes #161`. Galip's review is answered; waiting on
     his re-review.
  3. **#180** `hasan/12-snapshot-export` — `Closes #12`, CI 5/5 green, waiting on both reviews.
     Its ADR `2026-11-01-snapshot-schema-v0` is `Proposed` and needs all three of us.
- Review queue: **empty**. omer's #179 is reviewed and approved (2026-11-01).

## Why the D1 ADR says `Accepted` without two approvals on the PR

Both reviewers wrote "I agree with the decision" (galip 2026-10-31, omer 2026-11-01), each on the
one condition that their review points were folded in — and they are (a488608, 004a741). So the
status line **names that evidence and those dates** rather than claiming a click that has not
happened, the way omer's problem-details ADR names who approved where. The chase comment says this
openly and offers to put it back to `Proposed` in one commit if either of them disagrees; the
content does not change either way. The reason for not waiting: step schema v0 (#134) reached
`main` as `Proposed` with its condition met and **is still wrong there**, and a dozen issues cite
D1. If this is ever contested, the two-line flip is the only thing to revert.

## What #179 settles for my own work (do not re-derive)

PR #179 (#60, omer) is approved, with ADR `2026-10-31-accounts-and-tokens`: opaque Bearer tokens,
SHA-256 hash in Neo4j, BCrypt passwords, 12 h sessions, never-expiring CI API tokens.

**For the #61 CLI runner (FR-23):**

- `Authorization: Bearer $AYNA_SERVER_TOKEN` on every call. An API token is a `kind: api` token on
  an ordinary tester account, created by an admin with `POST /api/users/{id}/tokens`, shown once,
  never expires, revoked only by `DELETE /api/tokens/{id}`. `POST /api/auth/logout` deliberately
  leaves API tokens alone, so a CI run cannot log itself out.
- 401 = missing / unknown / revoked / expired token, 403 = the role may not do this, both RFC 9457.
  FR-23 maps either to **exit 2**, so the CLI does not need to tell them apart for the exit code.
- **401 and 403 must not be retried** by the result-delivery backoff — a revoked token or a demoted
  CI account answers the same way for the rest of the run. Retry only unreachable / timeout / 5xx,
  then write `ayna-undelivered.jsonl` and exit 2. Same reasoning as NFR-45. I stated this in the
  review as the contract point and it is mine to implement in #61.
- A password change ends that account's sessions but **not** its API tokens, so an admin rotating
  their own password does not break the nightly run. `/api/health` stays public, so
  `ayna run --server URL` can say "no AYNA server there" before it has a token.
- `.env.example` has no `AYNA_SERVER_TOKEN` line — it is a CI-machine variable, not a Compose one.
  **I said I would add it with #61** unless omer does it first.
- Every write API takes `@AuthenticationPrincipal AynaPrincipal` and stores the acting user's id;
  `startedBy` on Run is #44 and `decidedBy` on HealingProposal is #74, so my #63 decision log
  inherits the same rule. Graph schema is v0.2 (`User`, `AuthToken`, `HAS_TOKEN`, `V0003`).

Three minor findings I left on #179 (none blocking, omer's to take or leave): `server/AGENTS.md`
overstates what `AuthIntegrationTest` checks (it reads the generated contract, so a `permitAll()`
without `@PublicEndpoint` goes unnoticed — the direction that actually opens a hole); the Electron
main process keeps the dead token after an admin changes their own password; and `FirstAdmin`
throws from an `ApplicationRunner`, so a hand-made "no active admin but the name is taken" state
stops the server from booting.

## Next step

1. **Wait for the two Approve clicks on #169**, then merge #169, then #170. Both reviewers are
   still in `reviewRequests`, so it is in their queues; the chase comment is the nudge.
2. Then **#180**'s reviews, and the ADRs that are `Proposed` although their condition is met.
3. New work after that: **#22** (element under cursor) and **#23** (win32 fallback) now have a
   working `recognition/` to build on.

## Open, not mine to close

- **Two ADRs still say `Proposed` although their condition is met**: `2026-10-27-step-schema-v0`
  (#13 — galip's, he owes the flip on `main`; #150 touches that file and is the natural place) and
  `2026-10-31-element-descriptor-v0` (#11 closed with three approvals, PR #175). D1 is no longer
  on this list.
- **`minLength: 1` cannot say "not only spaces"** in `snapshot.schema.json` and
  `element.schema.json`: a Java or TypeScript producer could write `"   "` and be valid. My
  recommendation is a non-whitespace `pattern` on every string property in both, one PR bumping
  both to 0.2, **after** #15 and #24 land against 0.1.
- `schemas/AGENTS.md` names only the step schema's tests, in `ai/`; the element and snapshot
  schemas are tested in `agent/`. It needs a line, but it is an `AGENTS.md`, so **ask the user**.
- **Only Python 3.13 exists on this machine**, while every module declares `>=3.11`. A green local
  run is **not** evidence that the version floor holds — see `learnings.md` 2026-11-01.
- Galip owes a decision from my #173 review: whether a model server that is **not running** should
  keep arriving as a 504 `timeout` on Windows (a closed loopback port times out here instead of
  being refused). Plus two one-liners: #173's IPv6 listen address, #176's explicit LF newline. From
  my #166 review he also owes the one-sided `dpi` fallback decision in the healing scorer; omer's
  half of that is settled by the proposal-schema 0.2 ADR (`dpi` on Element) and he takes it into
  #25.
- Small follow-up branch, not started: the pre-ADR ownership tables in `docs/working-agreement.md`
  §1 and `docs/README.md` (galip's #19 note), and the `requirements.txt` mentions in
  `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- **PR #138** is empty (0 files) because #143 carried its content to `main`; it should be
  **closed, not merged**. Side effect: `docs/requirements-workshop.md` is on `main` with §7 still
  the empty template, tracked by #19 — galip must fill it.
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not created by me. Worth
  finding out whose it is before someone builds on it.
- **`copilot-swe-agent[bot]`** has pushed merge commits to branches of mine (`d261faa` on
  `hasan/161-winforms-walk`, co-authored by omer) and once left a literal `<<<<<<< HEAD` marker in
  `memory-bank/decisions/README.md` that reached `main`; #160 removed it. **Check that file
  whenever that bot touches a branch of mine**, and ask omer what the bot is for. It also leaves a
  `copilot-pull-request-reviewer` COMMENTED review on PRs, which does not count as an approval.
- Unverified, one weekly-session check: a **second monitor at another scaling**. Every snapshot
  number so far is from one 120-DPI display, so `dpi` has only ever been 120 and no snapshot has
  had negative `bounds`.
- The KeePassXC auto-lock check stays pending in `tasks/21-pilot-apps-decision.md` and is only
  needed before KeePassXC is promoted to pilot 3.
- Inbox: handled up to 2026-10-31, **including omer's 2026-10-31 #60/#61 note, answered in the
  #179 review**. Do not delete the handled lines yet — PRs #150 and #126 still add lines to that
  file and `merge=union` would bring deleted ones back.

## Environment, so it is not re-derived

`agent/.venv` exists (`pip install -e ".[dev]"`); `eval` installs with
`.venv/Scripts/python.exe -m pip install -e "eval[dev]"` from the repo root (omer replaced
`eval/apps/trial/requirements.txt` in #122). `client/node_modules` is installed. KeePass 2's demo
database: `%USERPROFILE%\OneDrive\Belgeler\Database.kdbx`, password `ayna-demo`; the #161 driver
uses `C:\ayna-pilots\ayna-demo.kdbx` instead. For #179's server tests Docker and Java 21 are
needed — **neither was available in this session**, which is why I relied on CI there.
