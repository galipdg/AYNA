# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-12 (eighteenth session, continued: review and merge train on omer's instruction "review hasan's PRs and merge if all is OK; resolve my conflicts and merge")
- **Merged 2026-11-12** (squash): #229 (`413fefa`, #59 run report, closed), #228 (`58f389a`, #221 grid columns, closed; hasan's Windows check passed 7/7), #230 (`f86bf8f`, hasan's #33 sample app; I ran it on macOS: 32 passed / 1 skipped, the app starts on cocoa and admin/admin opens the customer list).
- **#68** (run history) PR #231 — `main` merged in; merge it once CI is green (omer's instruction). The by-hand check in the Electron app is still pending (steps in `memory-bank/tasks/68-run-history.md`, against the `ayna68` Compose stack on port 28080; tear it down after with `docker compose -p ayna68 down -v`).
- **Held: #224 (#52 contracts v1)** — it changes `schemas/`, which needs all three approvals; galip has not reviewed. Before merging: `git merge origin/main`, regenerate `docs/api/openapi.yaml` with `./mvnw test` (do not hand-merge), check the frozen REST copy against the new endpoints (#51 screenshots, #59 report, #221 columns, #68 app runs), rerun server + client tests and the `contracts` job. If #227 (#22) merges first, add `elementFromPoint` to `agent-rpc.schema.json` as part of 1.0 (every reply field nullable).
- **hasan's PRs**: approved #227 (#22 `elementFromPoint`, my change request answered in `142a6c6`) and #232 (his memory notes). Both conflict on `memory-bank/people/hasan/active.md` (overwrite-only) after #230 merged; resolving them means a push to hasan's branches.
- **Follow-ups owed** (from hasan's reviews): FR-35 failure `category` in `StepResultResponse` and the report before #224 freezes (with #63); hasan opens the CLI `--report` issue (omer said yes on #229); #226's client half; a client check of the agent's major `rpcVersion`; `--screenshots` in the load test (#152); the pick hotkey's client half is #24 once #227 merges.
- ADRs still **Proposed** on `main`, waiting for galip: `2026-11-08-run-screenshots-and-retention` (#51).
- **AGENTS.md** §2 lists hasan as `@HasanBerk18`; his login is `hasanberkyanikkaya` (reviewer requests fail with the old one). Changing AGENTS.md needs omer's OK.
- **Next step** (resume here): #231 merged → #224 when galip approves; then #24 (pick hotkey client half, after #227) or #44's client half (after hasan's #40).
- Follow-up issues still open (owner omer): #204 (`needs-windows-test`), #206 (#38 Windows findings). Issues left open on purpose: #17, #24, #183, #184, #185, #38 (see their PRs' "Part of" notes).
- Inbox: every item up to 2026-11-10 is handled; delete the handled items in a branch of their own (with `merge=union`, deleting them in several branches at once brings them back).
- Local branches of merged PRs and old worktrees (`omer/195-advisor-demo` in the main folder; `omer/15…`, `omer/53-sdd-final`, `omer/44-run-api`, `omer/221-grid-columns` in `.claude/worktrees/`) are still here; delete them only on omer's OK.
- Open questions: project licence undecided; Leotta [4] PDF unread; Electron renderer not visible to UIA on Windows (hasan, #17 comment); galip's ADR approval on runs-api-and-live-updates.
- Network: SSH to github.com times out. Fetch and push over HTTPS: `git -c credential.helper='!gh auth git-credential' -c url."https://github.com/".insteadOf="git@github.com:" push origin <branch>` — one push per command.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` (regenerates `docs/api/openapi.yaml`; commit it). Stale surefire reports survive a branch switch; count only fresh ones. A worktree needs its own `npm ci` in `client/`.
