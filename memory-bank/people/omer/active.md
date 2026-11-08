# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-08 (sixteenth session: #204 in PR #219)
- **Open PRs of omer's, all waiting for reviews:**
  - #217 (#207 demo seed, window notes), #218 (#203 wording), #219 (#204 Spy follow-ups, Part of #204);
  - #126 (literature review part 1, #10): green, no approval.

  Each branch carries its own session-end memory, so `active.md` will conflict at every merge after
  the first: keep the newest file (this one is newer than #217's). `journal.md` is `merge=union`.
- **Merge order traps:**
  - #217 adds `client/src/main/__tests__/demoSeed.test.ts`, which reads `dev/mock/snapshot.json`; #219
    deletes that file. Whichever merges second points the test at
    `schemas/examples/snapshot/trial-login.json`.
  - #218 and #219 both add lines in `i18n/en.ts` / `tr.ts` near the Spy texts and `agentErrors`.
- **#204** (`omer/204-spy-followups`, task note `memory-bank/tasks/204-spy-followups.md`): points 1–7
  done, 8 (galip's dev-only `Desktop`) left to galip. Point 6 fixed on macOS (tree width no longer
  follows the rows drawn), still to be measured on VS Code: the 7-step Windows check is a comment on
  #204, label `needs-windows-test`. #204 stays open until that passes (the PR says "Part of").
- **Issues open on purpose:** #17 (`needs-windows-test`), #24 (hotkey needs #22), #183 (team review),
  #184 (Windows steps 2 and 6; step 6 is #204's point 6), #185 (galip's RS NFR-17 / TBD-2), #38
  (→ #206), #206 (`needs-windows-test`, close by hand with evidence), #28 (G0, team).
- **Next step** (resume here): #205 (SelectRow / step schema 0.2 rows in the editor), unblocked since
  #150 merged. Then #53 (SDD §7 rows; §RQ1 path `eval/spikes/uia_tree_dump.py`, inbox #199).
- **Open from reviews:** #209 (hasan): `.env.example`'s `AYNA_SERVER_URL` is read by nothing; #199:
  `eval` `testpaths` still excludes `spikes` (omer's call).
- **Local branches of merged work** (`omer/17…`, `omer/24…`, `omer/25…`, `omer/183…`, `omer/184…`,
  `omer/185…`, `omer/30…`, `omer/38…`, `omer/196…`, `omer/206…`, `omer/213…`,
  `omer/28-windows-guide`): delete only on omer's OK. Worktrees under `.claude/worktrees/`: several
  merged ones plus `spy-followups-week-4-72f1f3` (this session, `omer/204-spy-followups`).
- **Open questions:** project licence undecided; Leotta [4] PDF unread; Electron renderer not visible to
  UIA on Windows (hasan, #17 comment); galip's ADR approval on runs-api-and-live-updates.
- **Network:** SSH to github.com times out (port 22 and 443). Fetch and push over HTTPS, one push per
  command: `git -c credential.helper= -c credential.helper='!gh auth git-credential' -c
  url."https://github.com/".insteadOf="git@github.com:" push origin <branch>`. On 2026-11-08
  `gh pr create --reviewer HasanBerk18,galipdg` worked.
- **Local env:** a new worktree has no `client/node_modules`: `ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm ci`
  first, or `steps`/`testCases` tests fail on the missing Ajv. Client: `npm run lint && npm run
  typecheck && npm test` (211 on #219). `ruff` is in the main folder's `agent/.venv`.
  `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` regenerates `docs/api/openapi.yaml`.
