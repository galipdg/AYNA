# #221 Table column headers from capture to the editor's column dropdown

- Issue: https://github.com/galipdg/AYNA/issues/221
- Owner: omer · Branch: `omer/221-grid-columns`
- Started: 2026-11-10 · Last update: 2026-11-10

## Approach
- No snapshot-schema change and no agent work (hasan on #221): the agent already captures a grid's `Header` / `HeaderItem` elements in the ControlView tree.
- No graph change either: every Element keeps `siblingIndex`, so the server rebuilds the header order from the tree at read time. `server/.../repository/GridColumns.java` holds the rule and a Cypher fragment; `RepoObjectService.list` and `latestElement` use it. `columns` is in `RepoObjectSummary` and `RepoObjectResponse`, from the object's latest capture.
- Rule: (1) a `Header` child with named `HeaderItem`s → their names (KeePass 2's List, WPF); (2) only for Table/DataGrid: direct Header/HeaderItem children before the first DataItem/ListItem, without those lying wholly left of that cell (Qt row headers `1`, `2`). Blank names dropped, each name once.
- Client: `ColumnField` in `StepTable.tsx` is a `<select>` of the columns plus "Other…" (free text), or plain text when there are none. A stored column not in the list shows as typed text.

## Decisions (small, local to this task)
- 2026-11-10 — headers are computed at read time, not stored on RepoObject as ADR `2026-10-28-step-schema-v0-2-rows` "Editor" said — the graph already has the order (`siblingIndex`); storing them would mean a graph change, an ADR and stale copies when a new version is captured. omer first agreed to an `Element.columns` property + ADR on the wrong assumption that the graph loses sibling order; the read-time way needs neither.
- 2026-11-10 — the dropdown keeps an "Other…" free-text entry — the list can be incomplete (virtualised or scrolled-out headers), so a dropdown-only field could block a correct column.
- 2026-11-10 — the direct-header rule is not applied to a List — a List's `Header` is a container whose own name ("Header Control") would show up as a column when its items are not captured.

## Status
- [x] Server: `GridColumns` + `columns` in the repository API, unit + integration tests
- [x] Client: `columns` through `main/repository.ts`, `ColumnField`, en/tr
- [x] SDD §3.3 row
- [x] Issue criteria rewritten on GitHub (2026-11-10, omer's OK)
- [x] PR #228 (reviews: hasan, galip); Windows check posted on #221 with `needs-windows-test` (2026-11-10)
- Next step: answer the reviews; at the Windows session run the #221 check; if it has not run by merge, change the PR body to "Part of #221".

## Manual checks
- pending Windows session · hasan + omer · KeePass 2 entry list and a Qt `QTableWidget` give the right dropdown (posted on #221 2026-11-10; steps below).

### Check to post on #221

The server builds `columns` from the captured `Header` / `HeaderItem` elements. The Qt rule comes from the text of `eval/spikes/grid-probes.md`, not from a real snapshot, so it needs a real capture.

#### Setup
1. `git switch omer/221-grid-columns && git pull --ff-only`
2. Backend: `docker compose up --build -d` from the repo root, then `curl localhost:8080/api/health` → `{"status":"UP",…}`
3. Client: `cd client && npm ci && npm run dev`, then sign in
4. KeePass 2 with the demo database: `python eval/spikes/kp_state.py main`
5. Qt table: `python eval/spikes/grid_probe_app.py` (window *GridProbeWindow*)

#### Steps
1. Object Spy → capture KeePass 2's main window → import it under an application and version (e.g. "KeePass 2" / "2.57").
   *Expected:* the import succeeds.
2. Pick the entry list (`m_lvEntries`, List) → add it to the repository as `main.entryList`.
   *Expected:* it is saved.
3. Tests → new test → add a step: **Verify** on `main.entryList` → property *row exists* → row *by text* → open the "in column" field.
   *Expected:* a dropdown with *any column*, Title, User Name, Password, URL, Notes, *Other…*.
4. Pick *Other…*.
   *Expected:* a text box appears next to it; type `Foo` and close the cell; reopen it: the field shows *Other…* with `Foo`.
5. Repeat steps 1–2 for *GridProbeWindow*: add `customerGrid` (Table) as `probe.customerGrid`.
6. On it: **Verify** → property *cell* → open the column field.
   *Expected:* a dropdown with *Choose a column*, Ad, Soyad, Şehir, *Other…*. **Not** `1`, `2` or `3` (those are row headers).
7. (If at hand) HandBrake's queue or any WPF `DataGrid`: same as step 6.
   *Expected:* its column headers, or plain free text if it exposes no `Header`.

#### Report back
Pass or fail for each step. For a failure: a screenshot, the snapshot file (Spy → save) and the `GET /api/apps/{appId}/repo-objects` response for that object (`columns` field), plus the app version, Windows version and display scaling.


## Open issues
- #37 (galip): the ADR plans to narrow `column` to an `enum` of `columns`; with an incomplete list that rejects a correct column. Told galip (inbox).
- Not checked on a real capture yet: whether a WPF `DataGrid` (HandBrake) exposes a `Header` with `HeaderItem`s.

## Handoff
- Old snapshots work too: nothing is stored at import, so the headers appear for objects added before this change.

## Outcome (fill when the issue closes)
