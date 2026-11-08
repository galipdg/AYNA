# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-08 (fourteenth session, end: everything open is merged)
- **`main` at the end of the session** (`3bf3f15`): the whole client stack (#154, #186–#192, #197), plus:
  - #209 (#208);
  - #214 (CI Electron cache, #213 closed);
  - #215 (#206 fixes);
  - #216 (`DEMO-windows.md`, Refs #28);
  - #150 (galip, step schema 0.2);
  - #210 (hasan, #199 closed);
  - #211 (galip, #71);
  - #212 (memory).

  The only open PR is #126 (literature review part 1, #10): green, no approval.
- **CI**: on 2026-11-08 the client job's `npm run build` often failed with a 503/504 on electron-builder's `SHASUMS256.txt` request to GitHub. #214 caches `~/.cache/electron*` (key: `client/package-lock.json`). A cached zip skips that request: 0.09 s instead of 2 min. PR caches are not shared, so the cache helps every PR only once a green `main` run has saved it. A rerun of the failed job fixed #210–#212 (a rerun keeps the old merge commit's workflow).
- **Issues open on purpose:**
  - #17 (`needs-windows-test`: status bar, Start again, quit on Windows);
  - #24 (hotkey needs #22);
  - #183 (team review of the wireframes, hand check);
  - #184 (Windows steps 2 and 6);
  - #185 (galip's RS NFR-17 / TBD-2);
  - #38 (Windows findings → #206);
  - #206 (`needs-windows-test`: a 6-step re-run is posted on the issue, then close it by hand with the evidence);
  - #28 (G0, team; the LLM criterion is galip's).
- **Next step** (resume here): Week 4 issues, earliest first:
  - #207: demo seed backups (use #187's suggestion: `name` + `controlType`), the DEMO.md capture note, the Chromium 125+ line in `client/AGENTS.md`, minimum window width vs the 1280 px step table;
  - then #203, #204;
  - #205 (step schema 0.2 rows) is unblocked now that #150 has merged.

  Also, at the next #53 step: in `docs/sdd/SDD.md` §RQ1 (line ~868), `eval/spikes/uia_dump.py` → `eval/spikes/uia_tree_dump.py` (inbox #199).
- **Windows session**: hasan follows `DEMO-windows.md` (new, never run on Windows: fix any step that does not work as written). The queue is `gh issue list --label needs-windows-test`.
- **Open from reviews:**
  - #209 (hasan): `.env.example`'s `AYNA_SERVER_URL` is read by nothing (wire it for the CLI #61, or say it is reserved); binding to `127.0.0.1:` trade-off.
  - #199 (2): `eval` `testpaths` still `["apps/trial/tests"]`, so the spikes run in no CI job (omer's call; hasan offered to widen it).
- **Inbox** cleaned 2026-11-08: only the #199 SDD path item is left.
- **Local branches of merged work** (`omer/17…`, `omer/24…`, `omer/25…`, `omer/183…`, `omer/184…`, `omer/185…`, `omer/30…`, `omer/38…`, `omer/196…`, `omer/206…`, `omer/213…`, `omer/28-windows-guide`): delete only on omer's OK.
- **Worktrees:**
  - main folder: `omer/195-advisor-demo`;
  - `.claude/worktrees/`: `omer/15-snapshot-import`, `omer/53-sdd-final`, `omer/44-run-api`, `omer/208-compose-port` (all merged);
  - `client-stack-merges-08a13a` (this session).
- **Open questions:** project licence undecided; Leotta [4] PDF unread; Electron renderer not visible to UIA on Windows (hasan, #17 comment); galip's ADR approval on runs-api-and-live-updates.
- **Network:** SSH to github.com times out. Fetch and push over HTTPS, one push per command: `git -c credential.helper='!gh auth git-credential' -c url."https://github.com/".insteadOf="git@github.com:" push origin <branch>`. `gh pr create --reviewer` fails with a GraphQL error; use `gh api -X POST repos/galipdg/AYNA/pulls/<n>/requested_reviewers -f 'reviewers[]=…'`.
- **Local env:** `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` regenerates `docs/api/openapi.yaml`; commit it. Client: `npm run lint && npm run typecheck && npm test` (201 tests on `main`). Neither `ai/.venv` nor `agent/.venv` in the main folder has PySide6.
