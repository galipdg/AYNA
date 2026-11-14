# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-14. **The current copy of this file lives on `hasan/29-rq1-measure`**,
  not here: this branch carries only what #221's notes need, plus `main`'s facts as of #227's
  merge. When this branch merges, keep the 29-branch's header and this branch's own
  "omer's #221 Windows check" section — it is the one section `main` does not have.
- Current issue: **#40 (Playback v1, Week 5, due 23 Nov)** on `hasan/40-playback-v1`.
  All six keywords are implemented, all three criteria are tested, **and the Windows check ran
  here on 2026-11-14: 7 of 7 pass — but only after four fixes (`b28f2b9`)**. `Wait` and the
  ready gate (`826b386`), `Verify` (`ca51c83`), `Select` (`f36f1b3`), `SelectRow` + the three
  row checkpoints, then the four fixes. **623 agent tests pass, ruff clean, PR #237 open** with
  both reviews requested. **Read `memory-bank/tasks/40-playback-v1.md` before touching any of
  it**: the three row shapes, the duplicated column rule, the message wording and now the
  read-back ladder are all decisions with reasons.
- **The four defects the check found are the lesson of this issue, not a footnote.** All four
  needed a real provider and all four passed 612 unit tests. (1) **The pattern lookup never
  unwrapped the element** — `get_elem_interface` needs the raw `IUIAutomationElement`, the walk
  hands out a `UIAElementInfo`, and only #26's `actions.py` unwrapped it, so on real Windows
  *every* pattern read #40 added was silently "unsupported": Select, SelectRow, Verify's
  value/checked/selected, `cell`, `rowCount`. It is now done once inside `uia_patterns`.
  (2) **`Select` reported a choice it had not made** — Qt's `SelectionItem.Select()` returns
  cleanly, changes nothing, and the item then says `IsSelected` true. Every rung is now
  confirmed by reading the **target** back. (3) `LegacyIAccessible.DoDefaultAction` joined the
  ladder: the only rung Qt honours. (4) The box was expanded **once**, and Qt's popup shuts
  itself ~1 s later, so a late-filling list stayed invisible for good.
- **Next on #40: push `b28f2b9` + the memory, post the result as a comment on #40, remove
  `needs-windows-test`, and re-request both reviews** — the PR changed under them.
- **SC-20 is unblocked and #33's Qt finding is overturned** (too broad): UIA *can* choose an
  item in a Qt combo box, the popup's items *are* in the window's tree once expanded, and
  `LegacyIAccessible.DoDefaultAction()` on the item works. In galip's inbox.
- **The driver for a manual `runSteps` check does not exist in the repo** and had to be written
  from scratch (scratchpad, not committed): `UiaDesktop()` + `setup()`, `list_windows()` to pick
  the handle, then `desktop.run_steps(handle, document, targets)` — the `rpc.py` path with the
  socket taken out. `ayna_agent` is **not** pip-installed in the root `.venv`; use
  `agent/.venv/Scripts/python.exe`, which has it editable along with `websockets`. Worth a
  committed `ayna_cli` subcommand when #61 starts, because every future playback check needs it.
- **The sample app's grid is empty until a search runs**, so any grid step needs a `Click` on
  `refreshButton` first, and `--screen main` skips the login. The automation ids are Qt-prefixed:
  `QApplication.main.customerGrid`, not `customerGrid`.
- **This file is now spread over four branches and no copy is complete.** `hasan/29-rq1-measure`
  has the long review history and #29; `hasan/162-windows-llm-latency` has #162 and #23's
  summary; this one has #40. **Whichever merges last keeps every branch's own section.** Also:
  `eval/pyproject.toml`'s `testpaths` line is edited on the #29 *and* #162 branches and **will
  conflict** -- keep both entries (`rq1/tests` and `llm-latency/tests`).
- **#162 and #23 are delivered and out; #29 is waiting on a human.** PR **#235** (#162, no
  `Closes`: criterion 5 is galip's files) + issue comment `6876199863`. PR **#236** (#23,
  `Closes #23`) + comment `6876502627`. PR **#233** (#29, deliberately no `Closes`) needs the
  second labelling round, which the user postponed on 2026-11-14 -- the blind sheets and
  `measure.py agree` are committed and ready, so it needs a person's hour and nothing else.
- **PR #234 (omer, #24) reviewed 2026-11-14, CHANGES_REQUESTED**: `pickState` reads #22's three
  states correctly, but `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the Spy's own retry ladder
  captures for 30 s and 120 s and the agent serialises UIA calls on one worker thread -- so a
  pick pressed during a long capture shows a false `agent-error`. **I owe #24 its Windows check**
  after his fix: it is the first real test of the client's DIP -> physical conversion at 100 %
  and 150 %, the half #22's scaling evidence does not cover.
- **The Project status is settable again, and all four of mine are now `In progress`** (#23,
  #29, #40, #162). The token was missing `project`; the user granted it on 2026-11-14 with
  `gh auth refresh --hostname github.com --scopes project`. **`--hostname` is required**, because
  the shell here is non-interactive and `gh auth refresh -s project` alone exits with
  "--hostname required when not running interactively" -- which is what blocked every earlier
  session from touching the board.
- **#28's four acceptance criteria are all ticked** -- the earlier note saying "three of four,
  the last is galip's #7" was wrong. It stays open because its dependency **#24** is still open.
- **#22 is DONE and closed.** All three criteria are ticked, the scaling check ran here on
  2026-11-12 at 100 % and 150 % and passed at both, and **PR #227 was squash-merged on
  2026-11-14 (`bfcdb35`)**, which closed the issue. Nothing is left on it.
- **Merging a PR is the agent's prohibition, not the user's** (AGENTS.md §6 is addressed to the
  agent). The user has `push` on the repo, `protect-main` asks only for 1 approval, squash and
  resolved review threads, and there are **no bypass actors and no CODEOWNERS gate** on who
  merges. So an approved PR of mine is the user's to merge whenever they want — do not tell them
  it is waiting on omer, which is what the earlier "neither mine to merge" note was misread as.
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

## #40, so the next session does not re-derive it

`playback/runner.py` had the shape from #26 and `IMPLEMENTED = {"Click", "Type"}`; it is now
every keyword of step schema v0.2, with four new modules: `playback/checkpoint.py` (one
property of one element), `playback/tree.py` (one read of the window, plus the schema's single
rule for the text a cell or an item shows), `playback/items.py` (`Select`) and
`playback/rows.py` (`SelectRow` and the row checks). `agent/tests/grids.py` holds the three
measured row shapes for both row test files.

**The five decisions most likely to be re-derived or broken:**
- **`Select` is not a pure action**: a closed combo box has no items at all, so the target is
  expanded and the window **read again** before looking (#33) — **every poll it shows nothing,
  not once**, because Qt's popup closes itself. The ladder is `SelectionItem` → `Invoke` →
  `LegacyIAccessible.DoDefaultAction`, **each rung confirmed by reading the target back** with
  one `POLL_INTERVAL_S` of grace (Qt applies a choice 32 ms late). An editable box takes the
  text through `SetValue` only after the whole wait, and that value is read back too — with no
  grace, which is a known open issue now that a late-applying provider is known to exist.
- **Three row shapes, by structure not by framework**: the item is the row (KeePass 2), the
  items are the cells and only `GridItem` says which row they belong to (Qt has no row
  element), or the item is a one-cell row (`QListWidget`).
- **`playback/rows.py:columns_of` duplicates `server/.../GridColumns.java` on purpose** and
  must stay identical: that rule fills the dropdown the tester picked the column from, so a
  divergence reads the cell *next to* the one they meant. omer has this in his inbox.
- **`SelectRow` never uses `Invoke`** (it would *activate* the row and open a window); the
  fallback is MSAA's `LegacyIAccessible.Select`, which KeePass 2 needs.
- **A `SelectRow` on a cell-selecting view passes with a `message`** — the first passing step
  that carries one, which the ADR asks for and the run report (#59) renders.

- **"Ready" is the pre-step wait and it is more than "resolves"**: a step waits until the target
  resolves *and* is neither disabled nor off screen -- what the issue text asks for ("exists, is
  visible and enabled") and what the schema calls ready. #26 waited only for resolution, so a
  disabled element resolved at once and the step then failed inside `actions` for an unstated
  reason. **HandBrake is the real case from #29**: with no source loaded *every* tab reads
  `enabled: false`.
- `enabled`/`offscreen` of **`None` count as ready** -- a provider reporting neither is common
  and `NEVER_MATCH` already calls both unreliable, so refusing would time out every step of such
  an application.
- **A `Verify` waits only for resolution**, because a checkpoint may be *about* a disabled or
  offscreen element and would otherwise be unplayable.
- **Three of `Verify`'s six properties are not in a descriptor** and are read live: `value`
  (`ValuePattern`, then `LegacyIAccessible` -- the ladder `Type` writes down), `checked`
  (`TogglePattern` **On**, so indeterminate is *not* checked) and `selected`
  (`SelectionItemPattern`). `name`, `enabled` and `visible` come from the walk's descriptor.
- **"Cannot be read" is its own failure, not `false`** -- no `TogglePattern` on the target means
  the check does not apply, and "expected true, got false" would blame the application instead.
- **`expected: ""` matches an element with no text**, or an empty error label could never be
  verified. A target that vanishes mid-check reports *that*, not a property failure.
- **The target is re-resolved on every poll**, never kept: a re-read gives new live elements and
  the old one is a stale handle (the same reason #22 compares identity rather than geometry).
- **Message wording is fixed by the PR #231 review and the tests assert the exact strings**,
  because the run report (#59) is written against them. ` after N ms` for a check that re-read
  until the time ran out, `within N ms` for an element that never appeared -- two waits, two
  words. **#40's third criterion says "after N ms" for element-not-found while #26 shipped
  "within": keep `within`** and say so on the issue rather than changing it silently.
- **A field on a keyword that forbids it is refused, not ignored** (`value` on a Click, `row` on
  a Verify): ignoring it would play a mis-built document as something else and report `passed`.

## #23 -- the win32 fallback, answered and deliberately not built

- The elements win32 can see are exactly the ones UIA already names, the number it offers is
  literally the same `automationId`, and it is **not stable across runs** (7 of 8 control ids
  changed between two launches). Everything UIA cannot name has **no HWND at all**: 58 of 74 in
  KeePass 2, and HandBrake is 149 elements with **one** HWND, the window. WPF and Qt cannot gain
  anything, structurally.
- **The one genuine finding**: `e58`, a native Win32 `Edit` (class `Edit`, no `WindowsForms10.`
  prefix), kept control id **1001** across a restart -- real identity that `_GENERATED_ID` throws
  away for being a bare number. Candidate rule: trust a bare number from a native Win32 class,
  not from `WindowsForms10.*`. **Sample size one**, and `model.py` is normative under #11, so it
  needs an ADR and a `FEATURE_VERSION` bump. Open issue, not a change.
- `eval/spikes/win32_probe.py`, 19 tests off Windows; report `eval/spikes/win32-fallback.md`.
  **Three of those tests exist because the probe got it wrong first, each in the direction that
  flatters the fallback** -- do not simplify them away.
- **`UiaDesktop()` needs `setup()` called by hand** in a script; #29's harness and this probe
  both tripped over it. Asked galip for a line in `agent/AGENTS.md`.
- `eval/spikes/` is excluded from ruff and has no CI job, so its tests only run when someone
  names the path. Worth one issue together with `eval/pyproject.toml`'s `testpaths`.

## #162 -- NFR-12 on Windows, so it is not re-measured

Report `eval/llm-latency/report.md`, 13 result files under `eval/llm-latency/results/`.

- **The issue's premise was wrong about this machine**: it has an **RTX 3060 Laptop, 6 GB**, so
  the default numbers beat the Mac's. Forced CPU-only it is **2.7x slower than the Mac**.
- **`qwen3:8b` does not fit in 6 GB** (6.0 GB loaded, 30 % CPU / 70 % GPU); **`gemma4:e4b-it-qat`
  does** (3.1 GB, 100 % GPU). So gemma4 is **3.2x faster here** and matched the expected keywords
  **10/10 against 9/10** -- while being the *slower* of the two on the M2. "Which model is
  faster" is a question about the box, not the model.
- p50/p95 s: CLI qwen GPU **5.34 / 8.38**, CLI gemma GPU **1.65 / 2.47**, CLI qwen CPU
  **15.30 / 22.68**, HTTP qwen GPU **8.59 / 16.04**, HTTP qwen CPU **23.24 / 41.30**.
- **Recommended: a 60 s Windows deadline, not 30 s** (~1.4x the worst measured p95 of 43.33 s),
  and **`reasons` opt-in per request, default off** (#78) -- CPU-only it is p95 22.68 s with 0/10
  over the deadline against 43.10 s with 2/10.
- **A fully VRAM-resident model is almost immune to the machine's own load** (gemma4 1.65 ->
  1.70 s at 59 % busy; qwen3 5.34 -> 6.29 s). Under load the damage is in the **tail**.
- **Warm every offered model, not just the default**: a first request against a non-default model
  pays 14.71 s on the GPU and **25-51 s CPU-only**.
- **Output is not reproducible run to run at temperature 0 with seed 42** -- 1 of 10 sentences
  differed between two runs that differed only in machine load. Contradicts
  `ai/spikes/llm-smoke.md` and matters for **RQ3 (#77)**. In galip's inbox with the `reasons`
  toggle and criterion 5.
- Two gotchas now in `learnings.md`: a subclassed warm-up that skips `request_body` warms the
  wrong offload, and **Ollama reuses a runner already loaded CPU-only** (so `ollama stop` before
  a GPU run, and read `size_vram` instead of trusting the configuration you asked for).

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
telling him if #224 is about to land without them.

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
