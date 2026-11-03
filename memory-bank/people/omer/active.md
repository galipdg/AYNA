# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-03 (seventh session)
- Current issues: **#183** (client UI design + shell) on `omer/183-ui-design` (stacked on #25) and **#184** (three-panel Spy) on `omer/184-spy-workspace` (stacked on #183). Both built and committed locally, nothing pushed. Task notes: `tasks/183-ui-design.md`, `tasks/184-spy-workspace.md`.
- Next step: omer's feedback on the running client (light theme, Users, Settings, menus not yet looked at); then ask galip and hasan to review `docs/ui/` + the running client (README questions 1–6); then post #184's Windows check (in its task note) on the issue with `needs-windows-test`, after asking. #185 (Turkish/English, Week 4) after that.
- How to see it: server from `docker compose up`; in `client/`: `AYNA_AGENT_PYTHON=python3 PYTHONPATH=$PWD/dev/mock AYNA_MOCK_WINDOWS=$PWD/dev/mock/windows.json AYNA_MOCK_SNAPSHOT=$PWD/dev/mock/snapshot.json AYNA_MOCK_UIA=on npx electron-vite dev` (the mock stub server has no login).
- #25 done on `omer/25-repo-objects`: PR #187 (base main, carries #15, #17, #24). Server `POST /api/apps/{appId}/repo-objects`, client version bar + simplified form; both manual checks passed. Windows check with a real pilot app still pending (weekly session).
- Waiting:
  1. #15: PR #182 waits for review (hasan: schema reading; galip: `importInto` for #51/#74).
  2. #24: PR #186 ("Part of #24"); the hotkey selecting the element waits for #22 (`elementFromPoint`, hasan).
  3. #17: PR #154 (draft); `needs-windows-test` until the Windows re-run passes.
  4. #10: PR #126 (draft).
  Review order for omer's stack: #182, #154, #186, #187; after each merge, merge `origin/main` into the next branch.
- galip: inbox note on `omer/25-repo-objects` asks him to update RS NFR-17 / TBD-2 (UI language → Turkish and English, #185). It reaches him only when #187 merges; omer may tell him earlier.
- Board: the `gh` token may lack the `project` scope for Status changes (`gh auth refresh -s project`); `item-add` worked today.
- Inbox: nothing new. Delete the handled items once #150 has merged, so `merge=union` does not bring them back.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment); off-screen/minimized windows' highlight (#24 task note); GET for an imported snapshot (#15); #25 open issues (one Element behind several objects, no uniqueness constraint, generated-id rule copied from the agent).
- Network: SSH to github.com times out. Fetch and push over HTTPS with `git -c credential.helper='!gh auth git-credential' push https://github.com/galipdg/AYNA.git <branch>`; see `learnings.md`.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test`. Manual checks of server-backed screens: `docker compose up --build` + `cd client && npm run dev:mock`, server `http://127.0.0.1:8080`, admin from `.env` (the stub server has no login).
