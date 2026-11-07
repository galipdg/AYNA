# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-05 (eleventh session)
- Current issue: **#44**, server half done on `omer/44-run-api` (from `main`, not stacked): **PR #193** (`Part of #44`), reviewers galip and hasan, opened 2026-11-05. ADR `2026-11-05-runs-api-and-live-updates` is Proposed. Task note: `tasks/44-run-from-editor.md`. Client half waits for #38 on `main` and #40 (hasan; #26 under it has no branch).
- **#38** (step editor): PR #192, CI 5/5, manual check passed. After #191 merges, retarget #192 to `main` (merge `origin/main` in, never rebase).
- Windows check for #38 and #30 posted on #38 (2026-11-05), `needs-windows-test` added; run #184's check first. At the next sync of `omer/38-step-editor`, add "pending Windows session" to `tasks/38-step-editor.md` and `tasks/30-repository-view.md`. #24 and #25 are covered by #184's check.
- **#53**: first PR (SDD §5, §7, stale rows) runs in its own session on `omer/53-sdd-final`; §8 and the PDF wait for the final RS (#41).
- **#30** (Repository view): PR #191, reviewers galip and hasan; manual check passed 2026-11-04; Windows look at the weekly session.
- Merging: every PR of the stack is BLOCKED (`protect-main`: one approving review, threads resolved, squash only; Copilot reviews fail on quota; omer has no admin right). Ask omer before each merge. Do not merge #192 into `omer/30-repo-view`; merge #191 first, then #192, each only after its review and a yes from omer for that PR.
- #185: PR #190 still waits for galip's/hasan's wording review; ADR `2026-11-03-client-ui-language` stays Proposed until then. CI 5/5 (a flaky `ai` test was re-run; note in galip's inbox and on #190).
- Next step: check CI and reviews on #193 and on the stack (#182 → #192). After the stack merges, regenerate `docs/api/openapi.yaml` on whichever of #193 or the stack is second. The #44 client half starts when #38 is on `main` and #40 is done.
- G0 (#28, 9 Nov) at risk: #24 and #25 wait for review, #26 has no branch. #169 merged 2026-11-05 at omer's request (`ede430e`), #21 closed, so D1 is done. #170 synced with `main` on hasan's branch (`ca22253`), approvals kept. It failed the `ai` job three times on a race in galip's `_send` (9 of 1 500 on `main`, 0 of 1 500 with the log line moved before the response; verified fix in galip's inbox). omer's yes for #170 still stands if CI turns green; merge `origin/main` into it after the fix lands. #186–#191 will show a `learnings.md` conflict that `git merge origin/main` resolves.
- #38 open issues worth new issues: Import/Export buttons, searchable element menu + "Pick in Object Spy…", app switch drops unsaved steps, row duplicate/insert above (task note).
- How to see it: server from `docker compose up`; in `client/`: `AYNA_AGENT_PYTHON=python3 PYTHONPATH=$PWD/dev/mock AYNA_MOCK_WINDOWS=$PWD/dev/mock/windows.json AYNA_MOCK_SNAPSHOT=$PWD/dev/mock/snapshot.json AYNA_MOCK_UIA=on npx electron-vite dev`. Close older dev instances first (see `learnings.md`, 2026-11-03 HMR).
- #25 done on `omer/25-repo-objects`: PR #187 (base main, carries #15, #17, #24). Server `POST /api/apps/{appId}/repo-objects`, client version bar + simplified form; both manual checks passed. Windows check with a real pilot app still pending (weekly session).
- Waiting:
  1. #15: PR #182 waits for review (hasan: schema reading; galip: `importInto` for #51/#74).
  2. #24: PR #186 ("Part of #24"); the hotkey selecting the element waits for #22 (`elementFromPoint`, hasan).
  3. #17: PR #154 (draft); `needs-windows-test` until the Windows re-run passes.
  4. #10: PR #126 (draft).
  5. #183: PR #188; #184: PR #189 (`needs-windows-test`, step 8 waits for #22).
  Review order for omer's stack: #182, #154, #186, #187, #188, #189, #190, #191, #192; after each merge, merge `origin/main` into the next branch.
- galip: RS NFR-17 / TBD-2 (#185) is asked in PR #190's body and in an inbox note on `omer/25-repo-objects` (arrives when #187 merges).
- Board: the `gh` token may lack the `project` scope for Status changes (`gh auth refresh -s project`); `item-add` worked today.
- Inbox: nothing new. Delete the handled items once #150 has merged, so `merge=union` does not bring them back.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment); off-screen/minimized windows' highlight (#24 task note); GET for an imported snapshot (#15); #25 open issues (no uniqueness constraint, generated-id rule copied from the agent); #30: DETACH DELETE vs #74 proposals (asked galip on #191).
- Network: SSH to github.com times out. Fetch and push over HTTPS with `git -c credential.helper='!gh auth git-credential' push https://github.com/galipdg/AYNA.git <branch>`; see `learnings.md`.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test`. Manual checks of server-backed screens: `docker compose up --build` + `cd client && npm run dev:mock`, server `http://127.0.0.1:8080`, admin from `.env` (the stub server has no login).
