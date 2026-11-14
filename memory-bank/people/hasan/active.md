# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-12, end of a long session (#22's scaling check passed, omer's #221
  Windows check passed, #33 green). **This copy is the current one**: `main` still carries the
  2026-11-07 version, and the copies on `hasan/22-element-from-point` and `hasan/33-sample-app`
  are each one step behind. When any of those merges, take **this** file's version of the header
  and keep each branch's own sections.
- Current issue: **nothing in progress. Start #29** (RQ1 recognition measurement harness, Week 4,
  due 16 Nov) — it builds on the sample app that just landed in #33. One question for the user
  first: **#162 is overdue from Week 3**, and by AGENTS.md's earliest-milestone rule it should go
  before #29. #22 and #33 are both finished on my side and wait only on other people's reviews.
- **#22 is complete: all three acceptance criteria are ticked.** The scaling check ran here on
  2026-11-12 at 100 % and 150 %, passed at both, and the result with its numbers is a comment on
  the issue; `needs-windows-test` is removed. omer's `CHANGES_REQUESTED` was answered in
  `142a6c6` and the re-review is asked for again in a PR comment. **Nothing is left for me on
  #22 but waiting.**
- **#227** (`hasan/22-element-from-point`, `Closes #22`) — CI 5/5 green, **APPROVED by omer on
  2026-11-14**, `origin/main` merged in there on 2026-11-14 and 436 agent tests re-run green.
- **#230 is merged** (`f86bf8f`, 2026-11-12), so **#33 is done and the sample app is on `main`**.
  **#228 and #231 are merged too** (omer's grid columns and run history), and **#170, #200, #201**
  landed on 2026-11-07/08, so #161, #26 and the coordinate fixes are on `main`.
- `origin/main` is merged into this branch too (2026-11-14); this file was the only conflict,
  resolved by keeping this branch's version and folding #33's unique facts in below.
- **Review queue: empty.** omer's #228 (#221 grid columns) and #229 (#59 run report) approved
  2026-11-12, both with findings — see "What I owe from the 2026-11-12 reviews" below.
- **A third branch of mine is open: `hasan/221-windows-check-notes`**, cut from `main`, memory
  only (`learnings.md`, `journal.md`, this file). It exists because nothing of mine may be
  committed on omer's branch, which is where the #221 check had to run.

## omer's #221 Windows check — done 2026-11-12, 7 of 7 pass

Result and evidence are a comment on #221; `needs-windows-test` is removed, so **nothing of mine
blocks #228**. Recorded at the `columns` level rather than "the dropdown looked right", because
that field feeds the dropdown and is readable from
`GET /api/apps/{appId}/repo-objects`: KeePass 2 `main.entryList` →
`['Title','User Name','Password','URL','Notes']`; Qt `probe.customerGrid` →
`['Ad','Soyad','Şehir']` with **no** `1`/`2`/`3`; HandBrake 1.11.2 `queue.jobs` → `[]`.

**Step 7 did not test what it hoped to, and the report says so.** HandBrake's queue is a `List`
(`queueJobs`) with no `Header` child, not a WPF `DataGrid`, so it exercised the free-text
fallback. **The `DataGrid` branch is still unexercised** and nothing in `C:\ayna-pilots\`
exposes one — if it matters before the #52 freeze it needs another app.

Two deviations from omer's step text, both worth fixing in it: the health check is on **8081**
here (#208's `.env` escape; another program holds 8080 and answers 404), and the Qt window's
*title* is `AYNA Grid Probe` while `GridProbeWindow` is only in the automation id.

## #22, so the next session does not re-derive it

`elementFromPoint(x, y)` answers **out of the snapshot the agent took last**, returning that
snapshot's own element, rather than describing the hit element on its own. Three of the twelve
descriptor properties come from an element's surroundings (`nearestLabel`, `parentPath`,
`siblingIndex`), so describing one element costs a read per sibling *and* would give the same
element two different descriptors — the full reasoning is in `learnings.md` 2026-11-10 and it
applies to anything else that wants a descriptor outside a walk (#23, #54, a recorder).

Reply: `{handle, bounds, snapshotId, elementId, element}`, one shape for every outcome, and a
point is never an error. `snapshotId` null = nothing captured for this window; `snapshotId` set
with `elementId` null = the window changed, capture again; both set = select that node. omer has
this in his inbox, because the Spy's pick hotkey is what consumes it (#184 step 8).

**Identity decides, geometry only locates** (omer's #227 review, 2026-11-12). Every same-bounds
candidate goes to `CompareElements`, including a single one: a switched tab, a scrolled list and
a replaced wizard page all keep the rectangles, so a bounds-only lookup would have the Spy select
a stale node silently. The deepest-candidate fallback stays for the raw-view/control-view
disagreement but is gated on `controlType`, `name`, `automationId`. It costs nothing measurable.
`model._text` is now public as `model.text_value` for that comparison.

Measured here at 120 DPI, **with the check on**: median **2.2 ms**, p95 3.0 ms, worst 3.2 ms over
50 calls; a second run 2.5 / 3.7 / 4.2 ms (3.39 ms before the change, so it is inside the noise),
against #22's 300 ms. **436 agent tests pass, including the Windows ones; ruff clean.** All 50
measured calls named an element, so the hit test and the walk agree on identity for every element
of the trial window.

**Scaling, criterion 3 — done, pass at both** (2026-11-12, here, with the user changing the
scale in Settings). 23 tests pass at 100 % and at 150 %; **436 agent tests pass at 150 %**. The
evidence that the two scalings were real: `window dpi` 96 against 144, the login window
360 × 164 against 540 × 246 physical pixels (exactly 1.5×), `dpi_awareness()` `per-monitor-v2`
both times, and four points taken at a snapshot rectangle's centre answering with the **same
element id** at both scalings. Full table in the task note and in the #22 comment. What it does
*not* cover is the client's DIP → physical conversion (#184 step 8).

**Still to do:** nothing but omer's re-review, plus the schema `$defs` **only if #224 merges
first** — settled on #227: whichever of the two merges second adds them (#224 first → 1.1 here;
#227 first → omer folds it into 1.0). #224 was still open on 2026-11-12, so today this PR
carries no schema change.

## What I owe from the 2026-11-12 reviews

- **#229 (run report), the one finding worth acting on:** the endpoint holds every screenshot
  *and* the whole HTML in memory — measured arithmetic for its own NFR-09 case is ~58 MB peak in
  English and **~90 MB in Turkish**, because `Words.TR.title` contains `ı` (U+0131) and that one
  character flips the 15-million-char `StringBuilder` from LATIN1 to UTF-16. The ceiling is
  `ayna.screenshots.max-size` × `stepCount` = 400 MB of PNG, and the container has no `mem_limit`
  or `-Xmx`. Fix offered: `StreamingResponseBody` + `Base64.getEncoder().wrap(out)`. Relevant to
  me because **#54 sends the window, not the desktop**, which is what keeps the real size small.
- **#229 Q1 — `category` belongs in the step result before the freeze.** FR-35 names five
  categories *and* says the client shall show them; `docs/agent-rpc.md` already reserves the
  field for #63; the server's `StepResultResponse` has no place for it. If #224 freezes without
  it, FR-35's client half becomes a 1.1 bump. `expected`/`actual` for a Verify can wait — I will
  write `message` so a failed Verify names both values.
- **#229 Q2 — the CLI (#61) may save the report, as `--report <path>`, opt-in**, fetched *after*
  the last screenshot upload is accepted (the outbox orders result → screenshot, so a report taken
  at `finish` time can be missing images), and **a failed fetch never changes the exit code**.
  I offered to open it as its own issue rather than widen #61.
- **#229 small:** `repairProposed` is a documented step status with no words and no colour in the
  report (server 400s it until #74, so it is pre-emptive); times are UTC in Docker while the
  tester is at UTC+03:00 → `TZ` in `docker-compose.yml`.
- **#228 (grid columns) is verified, not just reviewed.** I ran omer's rule against real AYNA
  captures today: Qt `QTableWidget` → `['Ad','Soyad','Şehir']` (row header `1` at
  `[648,316,666,353]` excluded by one pixel against the first cell's left edge 667), KeePass 2
  `m_lvEntries` → the five `HeaderItem` names, `QListWidget` → `[]`. Two notes left on the PR:
  `<=` in the row-header test must not be tightened to `<`, and when no cell is captured
  (virtualised or a budget-truncated walk) the row headers cannot be excluded.
- **#221's UI half still needs the Windows session**: the dropdown in the running app with the
  server behind it (steps 3–4 of omer's check). The rule half is done.

## What I promised in the 2026-11-10 reviews

Keep these; they are commitments, not opinions.

- **#54 sends the target *window*, not the desktop** (said on #223). That is what makes omer's
  8 MB screenshot limit safe: I measured a 1920×1080 full-screen PNG at **222 KB** but the
  incompressible ceiling at that resolution at **7.92 MB**, i.e. the limit has no headroom for a
  full screen and none at all above 1080p. A window crop is a fraction of that.
- **#40 does not emit `repairProposed` until #74 is on `main`** (#223's ADR moves the write
  there). The server answers 400 today and under NFR-45 the result would be set aside instead of
  retried, so the healing experiment's own data would end up only in the undelivered file.
- **#61's outbox keeps order per `(runId, stepIndex)`** — the result, then its screenshot — and
  never attempts a screenshot whose result has not been accepted. This is what makes 404
  terminal; "no result yet" and "unknown run" are the same status in omer's contract, and I asked
  him for a 425 but took the ordering obligation either way. A screenshot whose result
  dead-lettered goes straight to `ayna-undelivered.jsonl`.
- **#61's terminal list grew:** 400 (including "not a PNG"), 401, 403, 404, 409, **413**, **415**.
  Retry: connection refused, DNS failure, timeout, 5xx.
- **The whitespace `pattern` on `snapshot.schema.json` and `element.schema.json` is 0.1 → 1.0,
  not 0.2.** Tightening a pattern is breaking under the #52 freeze; I proved it by running omer's
  `schema_compat.py` against my own schema (it rejects the 0.2 bump and allows 1.0). So it needs
  an ADR and all three approvals, after #15 and #24 have landed against 0.1, and the client's
  version-mismatch branch (#186) should expect `1.0`.
- **#221 may need nothing from me.** The column headers are already in every snapshot as
  `Header`/`HeaderItem` elements, so `RepoObject.columns` can be filled from the document the
  server already receives — no snapshot-schema change, no ADR, and it also covers KeePass 2,
  which `GetColumnHeaders` cannot (no TablePattern). Said so on #221; waiting for omer.
- **I will run `server/loadtest/run.sh` on Windows** (#225/#152) and report the `machine` block
  with Docker's NCPU/MemTotal. It cannot run as written: `python3` here is the Microsoft Store
  App Execution Alias stub, so the script dies at `python3 seed.py`. omer has the fix request.
- **#226 is mine to half-build**: the `blocked` flag on `SnapshotTimeout`. Galip owns the
  dispatcher line and the `-32002` doc row.

## Decisions already made — do not re-derive them

**#40 (playback v1):**
- **A primary set that matches more than one element is a failure**, FR-35 *element not found*.
  Playback **never picks the first match**: UIA child order is not stable across runs, so "the
  first" would make RQ2 (#69) measure AYNA's own nondeterminism. An ambiguous target does not
  start healing (FR-29): the remedy is another property, not another element. Fallback properties
  are tried only when the primary set matches **zero**.
- The result field is **`durationMs`**, and the steps to play are `document` from
  `POST /api/runs`, so `stepIndex` is a position in the run's own copy.
- **Rows on KeePass 2** (no Grid/Table pattern): read a row's cells from the `ListItem`'s `Text`
  children in header order; `{value, column}` maps the header text to a child index through the
  `Header`'s `HeaderItem`s. `cell` is grid-only in the schema while `rowExists {value, column}` is
  allowed on a list — the same column mapping, one forbidden and one required. Raised on #220 and
  #221; galip's v0.2 ADR to settle.

**Control types measured** (`eval/spikes/grid-probes.md`): Qt `QTableWidget` → `Table` (Grid +
Table patterns), Qt `QListWidget` → `List`, KeePass 2 `m_lvEntries` → `List` with a `Header` of
five `HeaderItem`s. No pilot app has a WinForms `DataGridView`.

## From #33 / PR #230, so merging `main` into this branch did not lose them

- **UI Automation cannot choose an item in a Qt combo box.** `SelectionItem.Select`, `Invoke`
  and `ValuePattern.SetValue` all leave it unchanged, and the items only exist after
  `ExpandCollapse`. **SC-20 needs that, so it is an open question for #40** and the reason the
  sample app's combo boxes cannot be driven the obvious way.
- **Reproduce CI before pushing anything under `eval/`:** `cd eval;
  ../.venv/Scripts/python.exe -m pytest -q`. CI runs a bare `pytest` from `eval/`, not
  `pytest eval` from the root, and the two disagree about which module wins when a name exists
  twice (#199, #210).
- For galip: `eval/apps/sample/texts.py` and `uia_check.py --json` are what
  `eval/nl/objects/sample.json` (#36) should be generated from.
- **#10's five literature entries are still owed** (PR #126 is a draft with no reviewer), and
  **#28 (G0 gate)** is open with three of four criteria ticked — the last one is galip's #7.
- `.codex/` sits untracked in my working tree (another CLI's hooks, my user's). Deliberately not
  committed and not ignored.

## Windows queue — the next real session

All omer's, all needing this machine:
- **#206** — the step editor's decimal comma and the stale-test-after-rename fix.
- **#204** — the Spy tree's scrolling **smoothness** at ~285 real Chromium-shaped elements, with
  the pane visible, reporting frame times rather than an impression. (The width part is fixed and
  measured; smoothness is the half my #184 note was actually about.)
- **#184** — step 2 (the Turkish fold) and step 6; step 8 is unblocked by #22 now.
- **#38** — the two findings are fixed in #206; re-run its check.
- **#17** — PR #154 is merged, so this is about the edge cases (crash, restart, a stale agent).
- **#225/#152** — the load test, for a second data point. Needs omer's `python3` fix first.
- **#197** — the check popover and the test-list resizer at 100 % **and** 150 %, `npm run demo`,
  and **Ctrl+Z / Ctrl+Y**, which were never pressed (only ⌘Z on macOS).
- ~~**#221** — the column dropdown in the running app~~ **done 2026-11-12, 7 of 7 pass.**
- ~~**#22** — the scaling check~~ **done 2026-11-12, pass at 100 % and 150 %.** Worth knowing for
  everything else in this queue: a scale change in Settings **needs no sign-out** — it applies to
  apps started afterwards, so a test that launches its own app sees the new scale at once. That
  makes #197's "at 100 % **and** 150 %" cheap to batch with any other scaling check in one
  session. Confirm the scale from a **DPI-aware** probe, never from plain PowerShell
  (`learnings.md` 2026-11-12).
- New: the **nav at 1280 px** — "Nesne Deposu" is the longest nav label now and it collapses to
  icons below 1180.
- **A second monitor at another scaling is impossible here**: this machine has one 1920×1080
  display. Say that plainly rather than listing it as pending.

## Environment, so it is not re-derived

- `agent/.venv` has pywinauto 0.6.9, ruff 0.17.3 and pytest; the repo-root `.venv` has PySide6 and
  is what the trial app and the Windows playback tests look for. **Python 3.13 only** — a green
  local run is never evidence that the `>=3.11` floor holds (`learnings.md` 2026-11-01). Run ruff
  as `agent/.venv/Scripts/python.exe -m ruff`; the root `.venv` has no ruff.
- **`python3` is a Store stub here**, `python` is the real 3.13.0. Any script that hard-codes
  `python3` fails on this machine.
- Docker **29.6.1** is available. Server address is **`http://[::1]:8080`**, not `localhost`:
  `PEMHTTPD-x64` holds IPv4 8080 and cannot be stopped without elevation. Admin is
  `admin` / `ayna-dev-admin` (the git-ignored `.env`).
- The database is **seeded and stopped, not deleted** (`ayna_neo4j-data` is intact): `AYNA Trial`
  with five repository objects and two tests. `docker compose start` brings it back. The #152 load
  test uses its own project `ayna-loadtest`, so its `down -v` cannot touch this — checked.
- **Rebuild the server when you switch branches** (`docker compose up --build`); nothing ties the
  running image to the checkout. This cost time on #38.
- This display is at **125 % (120 DPI)**, so "100 %" is not the resting state either.
- `client/node_modules` is installed; electron is 45.0.0, well past the Chromium that CSS anchor
  positioning needs. Pilot apps are in `C:\ayna-pilots\` with the demo vault `ayna-demo.kdbx`
  (password `ayna-demo`); `eval/spikes/kp_state.py main` opens KeePass 2's database in ~16 s.
- **Always name the path when running eval tests** (`pytest eval/apps/trial/tests`): #210 fixed
  the module collision, but `eval/spikes/` tests are still in no CI job.

## Open, not mine to close

- Three places answer `rpcVersion` `"0.1"` while #224 freezes the contract at 1.0:
  `agent/ayna_agent/rpc.py:37` (galip's, in his inbox), `client/dev/mock/ayna_agent/rpc.py:77`
  (omer's own, raised on #224) and two lines of `docs/agent-rpc.md`.
- **Nothing enforces the major version on the client ↔ agent link**: the client never reads
  `rpcVersion`, so a 2.0 agent would be used by a 1.x client. Offered to open an issue on #224.
- `DEMO-windows.md` §5.3 step 6 says `user` → 3 matches; the real number is **2** (computed
  against the committed capture). Raised on #218.
- The Spy's `visible` is "Ekranda" while the step editor's `visible` is "Görünür" — the *same*
  UIA property (`not IsOffscreen`, per the step schema's own description). Raised on #218.
- `DEMO.md`'s capture paragraph claims only `snapshotId` and `agentVersion` are test-supplied;
  the whole `capture` block and the `app` block are too. Raised on #217.
- #219's three new Turkish texts say "ajan", which #218's new test rejects — whichever merges
  second breaks `main` unless they are changed. Raised on both.
- Galip still owes, from earlier reviews: the model-server-not-running 504 `timeout` decision on
  Windows (#173), #173's IPv6 listen address, #176's explicit LF newline, and the one-sided `dpi`
  fallback in the healing scorer (#166). Plus #150's ADR sentence about KeePass 2 ListItems.
- **PR #138** is empty and should be **closed, not merged**.
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not mine. Find out whose.
- **`copilot-swe-agent[bot]`** has pushed to branches of mine and once left a `<<<<<<< HEAD`
  marker in `memory-bank/decisions/README.md` on `main`. Its `COMMENTED` review is not an
  approval.
- Inbox: handled through 2026-11-05. Do not delete the handled lines yet — open PRs still append
  to that file and `merge=union` would bring deletions back.
