# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-03 (fifth session)
- Current issue: **#25** (add element to the object repository), not started: no branch or task note yet. Proposed design waiting for omer's OK at the start of the next session:
  - `POST /api/apps/{appId}/repo-objects` with body `{logicalName, snapshotId, elementId, primary[], fallback[]}`. The issue text says `/api/repo-objects`; the app-scoped path matches the tests API.
  - The client first imports the snapshot (#15, idempotent), then links the new RepoObject to the server Element with `RESOLVES_TO {version}`. The Element is found by `(snapshotId, snapshotElementId)`.
  - The logical name uses the step schema's `screen.element` pattern. A duplicate name in the same app → 409. `none.noMatch` is refused (galip, #71).
  - Primary and fallback are suggested by the descriptor ADR's priority (`automationId` when not generated, `name`, `nearestLabel`, `className`, `parentPath`); the user edits them before saving. `bounds` and `dpi` are stored too (hasan's 2026-10-31 inbox request).
  - Open: Neo4j cannot store maps, so the property sets need parallel lists or a JSON string. This is a graph-model decision: ask omer.
  - Branch `omer/25-repo-objects` from `omer/15-snapshot-import` (stacked) until #182 merges.
- Waiting:
  1. #15: PR #182 waits for review (hasan: schema reading; galip: `importInto` for #51/#74). CI 5/5 at `e99aea5`; `fb825aa` (main + #179 merged, `createdBy`/`createdAt` on Window) pushed.
  2. #24 (`omer/24-object-spy`, stacked on #17, no PR of its own): waits for #22 (`elementFromPoint`, hasan) for the pick hotkey. Snapshot types are now checked against the merged schema (`0bdbc7e`).
  3. #17: PR #154 (draft); `needs-windows-test` until the Windows re-run passes. `main` (#179) merged in as `2fe42e0`.
  4. #10: PR #126 (draft), mergeable.
- Others' PRs: #169 and #170 (hasan) conflict with `main` only in hasan's own memory files (`decisions/README.md`, `hasan/active.md`); not touched. #150 (galip) is clean and approved.
- Board: #15 is still not "In progress" on the Project: the `gh` token lacks the `project` scope (`gh auth refresh -s project`).
- Inbox: nothing new. Everything up to 2026-11-01 is handled. hasan's DPI request (#14/#25): the Element side is done in #15; the RepoObject side belongs to #25. Delete the handled items once #150 has merged, so `merge=union` does not bring them back.
- Merge note: this file differs between `main` (from #179) and this branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 `workflow_dispatch` UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment), a candidate issue; off-screen/minimized windows' highlight (#24 task note, Open issues); GET endpoint for an imported snapshot (#15 Open issues).
- Network: SSH to github.com times out. Fetch and push over HTTPS with `git -c credential.helper='!gh auth git-credential' push https://github.com/galipdg/AYNA.git <branch>`; see `learnings.md`.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test`. The compose Neo4j volume holds V0003 from #60: a branch without it cannot start there, so use a throwaway Neo4j (`learnings.md` 2026-11-03). `agent/.venv` lacks `websockets`/`pywinauto`: `pip install -e ".[dev]"` before running the real agent.
