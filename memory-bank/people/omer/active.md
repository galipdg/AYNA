# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01 (second session)
- Current issue: **#24** (Object Spy) on `omer/24-object-spy` (stacked on `omer/17-agent-process-manager`, draft PR #154, no PR of its own yet). Window list, highlight, pick hotkey and the **property panel** (on `schemas/element.schema.json` 0.1, fed by the selected window for now) done; 77 client tests. Tree waits for #12 (snapshot schema), element under the cursor for #22. Task note: `tasks/24-object-spy.md`
- Next step:
  1. Property panel manual check by omer on macOS (steps in the #24 task note, "Manual checks"); pending.
  2. #60 PR **#179** (replaces #168): answer galip's and hasan's reviews; both must approve ADR `2026-10-31-accounts-and-tokens`.
  3. #17: Windows re-run requested on the issue (2026-11-01, 57 tests + "failed" message without INFO line); `needs-windows-test` stays until it passes, then PR #154 → `Closes #17`, ready for review.
  4. If #12/#22 still have not moved: #25 or #51.
- Merged 2026-11-01 at omer's explicit request: #178, #160, #155, #157 (#31, #158, #45, #48 closed). Not merged: galip's #173/#176/#150 (conflict on his side), #169 (galip's 4 points pending; I commented), #170 (after #169; approved).
- Inbox: 2026-10-31 items (galip #149, hasan #17) handled; items up to 2026-10-29 handled. Delete all of them once #150 has merged, so `merge=union` does not bring them back. #169 will add a DPI note (already settled by the 0.2 ADR, for #25).
- Merge note: this file differs on the #60 branch (#179) and this branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 `workflow_dispatch` UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment) — candidate issue
- Network: SSH to github.com is flaky (fetch sometimes works, push times out); push over HTTPS with `gh auth git-credential` (see `learnings.md`)
- Local env: `~/.zshrc` pointed `JAVA_HOME` at a removed JDK (`temurin-21.jdk`); omer fixes it with `/usr/libexec/java_home -v 21`. Until then run Maven as `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test`.
