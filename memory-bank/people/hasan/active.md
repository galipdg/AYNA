# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-14 (#29's first real captures and numbers; #227 and #232 merged).
  **This copy is the current one** and `main`'s is now only one merge behind it: this branch
  (#233) is the only place #29's facts live. `origin/main` is merged in as of `d788d64`.
- Current issue: **#29 (RQ1 recognition measurement harness, Week 4, due 16 Nov) is in progress**
  on `hasan/29-rq1-measure`, PR #233. The harness, the labelling guide and **35** tests are
  committed, and **the first captures and numbers are in** (`3c38247`, `47e2485`, `2137882`,
  pushed 2026-11-14). Posted to the team as a comment on #29.
- **#29's first numbers are unlabelled and must never be quoted as RQ1's rate**: HandBrake 45
  controls / 97.8 %, KeePass 2 53 / 100 %. The denominator is only what AYNA's walk found.
  What is left: the four screens behind a click (the check on #29), then labelling, then a rate.
- **The useful result is HandBrake's one unidentifiable control.** Of 8 toolbar buttons, 7 have
  both `automationId` and `name`; `e20` has neither and no `nearestLabel`, so its proposal
  escalates to `{className, parentPath}`, which all 8 share. **`siblingIndex` is the only
  property that would separate it, and `suggestUses` deliberately does not escalate to it** —
  UIA child order is not stable, the same reason #40 refuses "the first match". Asked omer on
  #29 to confirm it stays out; if he agrees it is a measured limit for #64's report, not a bug.
- **#227 and #232 are MERGED** (2026-11-14, `bfcdb35` and `d788d64`), so **#22 is closed** and
  #221's notes are on `main`. Both had been `CONFLICTING` on this file alone; each took an
  `origin/main` merge, and 436 agent tests were re-run green on #227's.
- **Merging a PR is the agent's prohibition, not the user's** (AGENTS.md §6 is addressed to the
  agent). The user has `push` on the repo, `protect-main` asks only for 1 approval, squash and
  resolved review threads, and there are **no bypass actors and no CODEOWNERS gate** on who
  merges. So an approved PR of mine is the user's to merge whenever they want — **do not tell
  them it is waiting on omer**, which is how the earlier "neither mine to merge" note got
  misread. The user asked about exactly this on 2026-11-14.
- **`capture` runs on `agent/.venv`, not the repo-root one** — `recognition/uia.py` takes its
  exception types from `ayna_agent.rpc`, which imports `websockets` at module level. galip has
  the request to decouple it; `rpc.py` is his file and is untouched.

## #162 is no longer blocked by a download

The user agreed to take #162 (overdue, Week 3) and #29 in parallel: pull the models in the
background, build #29 meanwhile. **Both models are now on this machine** — `qwen3:8b` (5.2 GB)
and `gemma4:e4b-it-qat` (6.1 GB), Ollama **0.40.16** answering on `127.0.0.1:11434`, 11 GB in
`%USERPROFILE%\.ollama\models`. Ollama was already installed when this session started, which
#162's body does not know: its first step is done.

**What #162 still needs is uninterrupted machine time, not a download.** Its own plan asks for
the batch idle *and* under load, so nothing else of mine may run during the idle half — which is
exactly why the captures for #29 and #162's runs cannot be done in the same sitting. The user
postponed both on 2026-11-12. Do #29's captures first (short, no CPU load), then leave the
machine alone for #162.

## #29, so the next session does not re-derive it

- **It measures with the product's code, not a copy.** `measure.py` puts `agent/` on `sys.path`
  and imports `ayna_agent.model` and `ayna_agent.playback.resolve`; both are UIA-free by
  contract, which is what lets the measuring half be tested off Windows. A test fails if either
  grows a pywinauto import.
- **"Recognised" = the Spy's own proposal matches exactly one element of the same window.** The
  rule is the client's `suggestUses` (`client/src/shared/repository.ts:98`), escalating along
  `automationId, name, nearestLabel, className, parentPath, controlType` and keeping a property
  only while it narrows. Not `model.primary_property()`, which returns a single property name and
  **is used nowhere** — measuring it would report a number no user ever sees.
- **The denominator is the honest part.** Without labels it is only what AYNA's walk found, so a
  control the walk missed pushes the rate up. `labelling.md` is the human enumeration
  (`control` / `ignore` / `missing`) and `--labels` makes it the denominator; every printed table
  says which one it used. **Never report the unlabelled rate as RQ1's rate.**
- Pilots are **HandBrake (P1)** and **KeePass 2 (P2)** per D1; KeePassXC is in `apps.json` but
  off by default. `eval/spikes/kp_state.py main|entry` reaches two of KeePass 2's four screens
  unattended in ~16 s; the rest need clicks and a manual check.
- PR for #29 **deliberately does not say `Closes #29`**: the harness is reviewable now but the
  issue's three criteria are not met. Getting galip and omer to agree the *definition* before
  numbers exist is worth more than after.
- **#22 is DONE and closed**, all three criteria ticked. The scaling check ran here on
  2026-11-12 at 100 % and 150 % and passed at both; omer's `CHANGES_REQUESTED` was answered in
  `142a6c6`, he approved on 2026-11-14 and PR #227 was squash-merged the same day.
- **#230 is merged** (`f86bf8f`, 2026-11-12), so **#33 is done and the sample app is on
  `main`**. Its `active.md` conflicted with this one exactly as expected; resolved on
  `hasan/29-rq1-measure` by keeping this header and folding its unique facts in below.
  **#228 and #231 are merged too**, so omer's grid columns and run history are on `main`.
- **One open PR of mine is left: #233** (#29, deliberately no `Closes`). #227 and #232 merged on
  2026-11-14; `hasan/221-windows-check-notes` is gone with #232.
- **Review queue: empty.** omer's #228 (#221 grid columns) and #229 (#59 run report) approved
  2026-11-12, both with findings — see "What I owe from the 2026-11-12 reviews" below.
- The `hasan/221-windows-check-notes` branch existed only because nothing of mine may be
  committed on omer's branch, which is where the #221 check had to run. It merged as #232 and
  is gone; the pattern is worth reusing the next time a check runs on someone else's branch.

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

**Still to do: nothing of mine, and the `$defs` are now omer's.** The agreement on #227 was that
whichever of #227 / #224 merged *second* adds `$defs/elementFromPointRequest` and
`elementFromPointResult` to the contract. **#227 merged first (2026-11-14, `bfcdb35`) and #224
is still open**, so omer folds them into 1.0 rather than me bumping anything to 1.1. Worth
telling him if #224 looks about to land without them.

## PR #231 (omer, run history, #68) — approved 2026-11-12, with one fix asked for

Full review is on the PR. The two questions he asked me are answered there and are commitments:

- **#61 does not want the app-wide run list**, and it must not be widened for it. `ayna run`
  gets its run id from `POST /api/runs`, so it never looks one up; a CI consumer would want
  "this test on this version" with paging, not the newest 100 of an application (≈ a day under
  #223's retention). What I do still want is the single run's report as `--report <path>`, its
  own issue, not a wider #61.
- **The failed-Verify wording is mine and I set it**, since #26 has no checkpoint to copy. House
  style from `playback/resolve.py` — lower case, logical name first, no "Step failed:" prefix:
  `login.message: name should contain "Invalid", it is "Welcome, admin!"`;
  `login.okButton: enabled should be true, it is false`;
  `main.customerGrid: rowCount should be 3, it is 5`;
  `main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does`. A checkpoint that
  re-read until the time ran out appends ` after 5000 ms`, matching "element not found"'s
  existing `within 5000 ms`. **#40 must use exactly these.**
- Asked him to fix before merge: the report temp files are deleted with a fire-and-forget
  `rm` in `will-quit`, which does not wait, so ~15 MB pages carrying screenshots of the
  application under test can survive in `%TEMP%`. `rmSync` plus a sweep at `whenReady`.
- Also told him the seed's `notRun` steps should carry `"not run: an earlier step failed"`, the
  message the real runner writes (`playback/runner.py:147`).

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

## From #33 / PR #230, so merging this file did not lose them

- **UI Automation cannot choose an item in a Qt combo box.** `SelectionItem.Select`, `Invoke`
  and `ValuePattern.SetValue` all leave it unchanged, and the items only exist after
  `ExpandCollapse`. **SC-20 needs that, so it is an open question for #40** and the reason the
  sample app's combo boxes cannot be driven the obvious way.
- **Reproduce CI before pushing anything under `eval/`:** `cd eval;
  ../.venv/Scripts/python.exe -m pytest -q`. CI runs a bare `pytest` from `eval/`, not
  `pytest eval` from the root, and the two disagree about which module wins when a name exists
  twice (#199, #210). This is why #29 had to add `rq1/tests` to `testpaths` — a green
  `pytest eval/rq1/tests` says nothing about CI.
- For galip: `eval/apps/sample/texts.py` and `uia_check.py --json` are what
  `eval/nl/objects/sample.json` (#36) should be generated from.
- **#10, my five literature entries, is still owed** (omer's inbox note of 2026-11-05); PR #126
  is still a draft and has no reviewer.
- **#33's three checkboxes were still empty on the closed issue**, and one of them really is not
  met: "runs with one command on every member's machine" holds for Windows and omer's macOS M3
  but **not galip's machine**. Recorded as a comment on #33 on 2026-11-12 rather than ticked, and
  galip is asked for one command there. Also answered omer's open question from his run: the
  login window staying visible beside the customers window is deliberate (SC-14).
- **#28 (G0 gate) is still open** with three of four criteria ticked; the last one is galip's #7.
- Of the inbox's entries only two are still live (#10's entries, and now nothing of #221's).
  **I offered to delete the handled ones; the user has not said yes, so they stay.**
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
- **#29's own captures (mine, not omer's)**: KeePass 2 `main` and `entry-editor` via
  `kp_state.py`, HandBrake `main-summary`, then `measure.py measure`. Short and CPU-light, so do
  it *before* leaving the machine idle for #162.
- **#231** — the Runs screen in the Electron app: the two dropdowns, "Raporu aç" in its own
  window, Kaydet… and the saved file opening offline, at 100 % **and** 150 %. Batch it with
  #197's Ctrl+Z/Ctrl+Y, which have never been pressed on Windows.
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
- **Ollama 0.40.16 is installed and running** on `127.0.0.1:11434`, with `qwen3:8b` and
  `gemma4:e4b-it-qat` pulled (11 GB in `%USERPROFILE%\.ollama\models`), as of 2026-11-12.
  #162's body says there is no Ollama here; that is out of date.
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
- **Review queue: empty again.** PR #231 was the only one waiting and it is approved.
- Inbox: handled through 2026-11-05. Do not delete the handled lines yet — open PRs still append
  to that file and `merge=union` would bring deletions back.
