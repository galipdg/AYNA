# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-03 (eighth session)
- Current issue: **#185** (Turkish/English UI) on `omer/185-ui-language` (stacked on #184): built, pushed, **PR #190** (review requested from galip and hasan; ADR `2026-11-03-client-ui-language` Proposed). CI 5/5 green (2026-11-03). Task note: `tasks/185-ui-language.md`.
- Next step: omer reads both languages on every screen (switch in the top bar); fold galip's/hasan's wording fixes into `client/src/renderer/src/i18n/tr.ts`; when the ADR is approved, set it Accepted. Then the next Week 4 issue (`gh issue list --assignee @me`).
- How to see it: server from `docker compose up`; in `client/`: `AYNA_AGENT_PYTHON=python3 PYTHONPATH=$PWD/dev/mock AYNA_MOCK_WINDOWS=$PWD/dev/mock/windows.json AYNA_MOCK_SNAPSHOT=$PWD/dev/mock/snapshot.json AYNA_MOCK_UIA=on npx electron-vite dev`. Close older dev instances first (see `learnings.md`, 2026-11-03 HMR).
- #25 done on `omer/25-repo-objects`: PR #187 (base main, carries #15, #17, #24). Server `POST /api/apps/{appId}/repo-objects`, client version bar + simplified form; both manual checks passed. Windows check with a real pilot app still pending (weekly session).
- Waiting:
  1. #15: PR #182 waits for review (hasan: schema reading; galip: `importInto` for #51/#74).
  2. #24: PR #186 ("Part of #24"); the hotkey selecting the element waits for #22 (`elementFromPoint`, hasan).
  3. #17: PR #154 (draft); `needs-windows-test` until the Windows re-run passes.
  4. #10: PR #126 (draft).
  5. #183: PR #188; #184: PR #189 (`needs-windows-test`, step 8 waits for #22).
  Review order for omer's stack: #182, #154, #186, #187, #188, #189, #190; after each merge, merge `origin/main` into the next branch.
- galip: RS NFR-17 / TBD-2 (#185) is asked in PR #190's body and in an inbox note on `omer/25-repo-objects` (arrives when #187 merges).
- Board: the `gh` token may lack the `project` scope for Status changes (`gh auth refresh -s project`); `item-add` worked today.
- Inbox: nothing new. Delete the handled items once #150 has merged, so `merge=union` does not bring them back.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment); off-screen/minimized windows' highlight (#24 task note); GET for an imported snapshot (#15); #25 open issues (one Element behind several objects, no uniqueness constraint, generated-id rule copied from the agent).
- Network: SSH to github.com times out. Fetch and push over HTTPS with `git -c credential.helper='!gh auth git-credential' push https://github.com/galipdg/AYNA.git <branch>`; see `learnings.md`.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test`. Manual checks of server-backed screens: `docker compose up --build` + `cd client && npm run dev:mock`, server `http://127.0.0.1:8080`, admin from `.env` (the stub server has no login).
