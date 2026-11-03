# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-03 (sixth session)
- Current issue: **#183** (client UI design, app shell and plain-language UI), not started: no branch or task note yet. Why: in #25's manual checks omer found the client hard to use and to present to the advisor, even after the form was simplified; the G0 demo (#28) is this week. First step: wireframes of every RS §3.5.1 screen + flows + a short style guide in `docs/ui/`, shown to omer (and the team) **before** any shell code. Then #184 (Spy as a three-panel workspace: windows | tree | properties + add to repository), then #185 (Turkish/English, Week 4).
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
