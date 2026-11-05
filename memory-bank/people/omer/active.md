# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-05 (tenth session)
- Current issue: none in progress. **#38** (codeless step editor) done on `omer/38-step-editor` (stacked on `omer/30-repo-view`): **PR #192**, reviewers galip and hasan, CI 5/5; omer's manual check passed 2026-11-05. Task note: `tasks/38-step-editor.md`. After #191 merges, retarget #192 to `main` (merge `origin/main` in, never rebase).
- **#30** (Repository view): PR #191, reviewers galip and hasan; manual check passed 2026-11-04; Windows look at the weekly session.
- Merging: omer allowed merging "if everything is OK" (2026-11-05), but every PR of the stack is BLOCKED (branch protection needs an approving review; Copilot reviews fail on quota). Do not merge #192 into `omer/30-repo-view`; merge #191 first, then #192, each only after its review and a yes from omer for that PR.
- #185: PR #190 still waits for galip's/hasan's wording review; ADR `2026-11-03-client-ui-language` stays Proposed until then. CI 5/5 (a flaky `ai` test was re-run; note in galip's inbox and on #190).
- Next step: check reviews on the stack (#182 → #192); then the next issue. #44 (run from the editor, Week 6) needs #38 and #40 (hasan's playback v1, still open) — check #40 before proposing it; otherwise take the earliest open Week 5/6 issue. Ask omer first.
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
