# #29 Recognition measurement harness (RQ1)

- Issue: https://github.com/galipdg/AYNA/issues/29
- Owner: hasan · Branch: `hasan/29-rq1-measure` · PR: #233 (**no `Closes`** — see below)
- Started: 2026-11-12 · Last update: 2026-11-12

## Approach

Two halves, split exactly where the repo already splits capture from rules:

1. **Capture is Windows-only and does nothing clever.** `measure.py capture <app>` drives the
   agent's own `recognition.UiaDesktop` (`list_windows` + `snapshot`) and writes the resulting
   `urn:ayna:schema:snapshot` document to `eval/rq1/snapshots/<app>/<screen>.json`. The operator
   opens the screens; nothing here tries to navigate a pilot app.
2. **Measurement is pure and runs anywhere.** `measure.py measure` reads those snapshot files and
   writes the CSVs. No UI Automation, so every rule is unit-tested in CI off Windows.

**It measures with the product's own code, not a copy of it.** `measure.py` puts `agent/` on
`sys.path` and imports `ayna_agent.model` and `ayna_agent.playback.resolve` — both are
deliberately UIA-free, so they import on any OS with no new dependency and no CI change. The
alternative was a third copy of the identification rule in `eval/`, which would have made RQ1
measure the harness instead of AYNA.

**What counts as recognised.** SDD §6 says "AYNA identifies the control uniquely from its
descriptor". Made exact here as: build the property set the Spy would propose for the control
(`client/src/shared/repository.ts:98 suggestUses` — the priority's fields in order, a field kept
only when it narrows the match, a generated `automationId` skipped), then count the elements of
the **same window** that match it with `playback.resolve.matches`. Exactly one → recognised.
Scope is the window, because that is the scope the Spy counts in and the scope playback resolves
in.

**What counts as a control.** #6's interactive set (15 control types, `TitleBar` subtrees
excluded), kept identical on purpose so RQ1's numbers sit next to the D1 table in
`eval/spikes/uia-dump.md` and the two can be compared.

Pilots are **HandBrake (P1, WPF)** and **KeePass 2 (P2, WinForms)** per the D1 ADR; KeePassXC is
registered but off by default, as D1 makes it conditional.

## Decisions (small, local to this task)

- 2026-11-12 — **Measure the client's escalating proposal, not `model.primary_property()`** —
  `primary_property()` returns one property name and is used nowhere; `suggestUses` is what a
  tester actually gets when they add an object. Measuring the unused rule would report a number
  no user ever sees. See "Open issues": the two rules disagree and that is worth an issue.
- 2026-11-12 — **Uniqueness is per window, not per app** — the Spy's `matchCount` and playback's
  `resolve` both work inside one window's snapshot. A cross-window number would be a different
  (and much worse) metric that nothing in the product relies on.
- 2026-11-12 — **Two CSVs per app, not one** — `*-rates.csv` carries the per-control-type rates
  the issue asks for; `*-controls.csv` is one row per control and doubles as the sheet a human
  labels for ground truth. The guide's procedure needs the per-control rows; the criterion needs
  the rates.
- 2026-11-12 — **Snapshots are committed and never re-captured for the same result** —
  `eval/AGENTS.md` already forbids editing a ground-truth file after an experiment used it. The
  snapshot is that file here: it is what makes a number re-derivable without the app.

## Status

- [x] Branch, task note, design settled
- [x] `eval/rq1/measure.py`, `apps.json`, tests (31), README — `ae9ab25`
- [x] `eval/rq1/labelling.md` (ground-truth guide) — `ae9ab25`
- [x] `eval/pyproject.toml`: `rq1/tests` in `testpaths`, `rq1` in ruff's `src`
- [x] **First captures and first (unlabelled) numbers** — 2026-11-14 on this machine
      (`3c38247`, corrected later the same day): KeePass 2 `main` (74 elements, 561 ms) and
      `entry-editor` (40, 291 ms); HandBrake `main-summary` is the user's 10:53 capture
      (118, `Open Source` enabled), not my 10:01 one, which caught the source picker. All
      captures so far have **0 read errors**.
- [x] **The screens behind a click — all of them, 2026-11-14 on this machine.** KeePass 2
      `open-database` (19 elements, 216 ms) and `options` (87, 1364 ms) at 10:35 and 10:51;
      HandBrake `preferences` (74, 826 ms) and `queue` (32, 236 ms) at 11:30 and 11:46. **Every
      capture 0 read errors**, and each verified against `apps.json`'s stated state from the
      snapshot content rather than from an impression: `open-database` carries `m_tbPassword`,
      `options` the Security tab's own options, `preferences` the General page with its
      `vlcPath` box, `queue` the `queueJobs` list with `0 jobs pending`.
- [x] **`main-video` is dropped from `apps.json`, not pending** — see below; the registry
      carries the reason in a `note` on the HandBrake entry.
- [x] **Ground-truth labelling, one screen per pilot** — `eval/rq1/labels/handbrake-queue.csv`
      (6 rows) and `eval/rq1/labels/keepass2-options.csv` (54 rows), 2026-11-14. The two
      screens were chosen because they carry the findings: `queue` has HandBrake's genuine
      failures and `options` has KeePass 2's 16 composite rows. `main-summary` was deliberately
      *not* labelled — it comes out 100 % and would hide the result.
- [ ] Post the corrected numbers to the team (third criterion)
- **Next step:** post the corrected numbers and the `e20` retraction to #29, fix the two errors
  in the check text there (the `agent/.venv` interpreter, HandBrake's real path), then decide
  with the user whether PR #233 takes `Closes #29` — all three acceptance criteria are met once
  the comment is posted.

### The first labelled rates, 2026-11-14 — these are the ones that may be reported

Per **screen**, because a ground-truth rate's unit is the labelled screen and not the app (see
"Open issues": `--labels` prints a hybrid app total). The `missing` sweep was run on both
screens by the user on this machine and found **nothing**, so no control escaped the walk.

| App | Screen | Controls | Recognised | Rate | `ignore` |
|---|---|---|---|---|---|
| HandBrake 1.11.2 | `queue` | 6 | 4 | **66.7 %** | 0 |
| KeePass 2 | `options` (Security) | 35 | 35 | **100 %** | 19 |

**The two rates fail in opposite directions, and that is the result.** KeePass 2's screen was
70.4 % unlabelled and is **100 %** labelled: all 19 dropped rows are non-controls — the inner
parts of the four `NumericUpDown` composites and three scroll-bar parts — so every control a
tester would target on that screen is uniquely identifiable. HandBrake's screen was unchanged
by labelling (all 6 rows are controls) and sits at **66.7 %**: `e14` (the `Options` split
button beside Start Queue) and `e19` (the `When Done` dropdown) are `MenuItem`s with **no
`automationId` and no `name`**, whose parent `Menu` carries the name instead, so `suggestUses`
escalates to `{className, parentPath}` and the two match each other.

**This is the shape of AYNA's real limit: nameless WPF `MenuItem`s inside a named `Menu`.** The
identity exists one level up the tree and the descriptor does not reach for it. It is not the
`siblingIndex` question `e20` looked like — these elements have real bounds, are enabled, and
are controls a tester targets.

### Numbers after the full check, 2026-11-14 — still unlabelled, so not RQ1's rate

| App | Screens | Controls | Recognised | Ambiguous | No property |
|---|---|---|---|---|---|
| HandBrake 1.11.2 (WPF) | 3 | 71 | 67 (94.4 %) | 4 | 0 |
| KeePass 2 (WinForms) | 4 | 118 | 102 (86.4 %) | 16 | 0 |

**Every one of the 20 unrecognised controls has one of exactly two causes**, which is the
result worth reporting. HandBrake's 4 are elements carrying **neither `automationId` nor
`name`** (`main-summary` `e20`, match 8; `preferences` `e28`, match 2; `queue` `e14` and `e19`,
match 2) — `suggestUses` escalates to `{className, parentPath}`, which their siblings share.
KeePass 2's 16 are the inner parts of four composite controls (below). The first is a real
limit of the descriptor; the second is what labelling removes.

**`main-video` cannot be staged and was dropped from the registry** (2026-11-14). Without a
source loaded **every** HandBrake tab reads `enabled: false`, Summary included, so the tab
cannot be selected — while loading a source would contradict this screen set's own "no source
loaded" state. The instruction contradicted itself. Measuring the tab pages needs a second
screen set with a source, which is not RQ1's question. Recorded as a `note` on the HandBrake
entry in `apps.json` so a reader does not re-derive it.

**`preferences` shares only 12 identity keys with `main-summary`, and `queue` is its own
window.** Worth measuring, because HandBrake 1.11 renders Preferences *inside* the main window
(same title, same bounds), which looks like the double-counting the source picker was deleted
for. It is not: the 12 shared keys are title-bar chrome, which `measure.py` already excludes,
whereas the source picker shared the whole menu, toolbar and tab strip.

KeePass 2 was 53 controls / 100 % on two screens; **`open-database` and `options` took it to
86.4 %**, which is the first evidence that two easy screens were flattering it.

**A capture is only evidence if the screen really was in the state `apps.json` names, and my
first HandBrake one was not.** The 10:01 capture (149 elements) was taken with the source
picker still up. It was caught by diffing a fresh capture against it — 118 elements against
149, and the 31 extra ones were the picker's own panel (`sourceSelection`, `Choose File to
Scan`, `Cancel`) — and confirmed by `enabled: false` on every toolbar button including
`Open Source`. The real `main-summary` was captured at 10:53 (118 elements, `Open Source`
enabled). **The numbers first posted to #29 — HandBrake 45 controls / 97.8 % — came from the
wrong state and the correction is owed on the issue.** The `e20` finding below survives
unchanged as a measurement but **its reading is retracted**: `e20` has **no `bounds` at all**,
`enabled: false`, and is a WPF `Button` with no name and no id — a toolbar template part that is
not rendered, so it is not a control and is labelled `ignore`. The claim posted to #29, that it
is "a control AYNA cannot identify", is **wrong and owed a correction**. The `siblingIndex`
question it raised with omer is therefore not grounded in this element; the genuine nameless
controls are `queue`'s two `MenuItem`s, and they would not be helped by `siblingIndex` either,
since their names live on the parent `Menu`.

The source-picker capture was then **deleted rather than registered as a screen**: it is the
same window with the same controls in a different `enabled` state, and `enabled` is in
`NEVER_MATCH` ("state, not identity"), so it adds nothing about *recognition* while
double-weighting that window. Recoverable from `ec63ef0` if a later question needs it.
**Check a new capture's state against `apps.json` before trusting it** — the cheap test is
whether the controls that should be live actually read `enabled: true`.

**The denominator is only what the walk found, and it is wrong in both directions at once** —
this corrects what the guide and this note used to say. A control the walk missed is invisible
and lifts the rate; every inner part of a composite control is counted as a target and lowers
it. Only labelling separates them, so **do not assume the labelled rate comes out lower**.

**All 16 of KeePass 2's ambiguous elements are one cause: composite controls.** The Options →
Security tab has four rows, each a WinForms `NumericUpDown` that reaches UIA as five elements —
the outer `Spinner` with a developer-chosen id (`m_numLockAfterGlobalTime`, **recognised**), an
inner `Edit` and inner `Spinner` with generated numeric ids, and `Up` / `Down` buttons with no
id. The four outer spinners are all recognised; the 16 inner parts are all ambiguous, because
the four composites expose identical names (`NumericUpDown`, `Spinner`, `Up`, `Down`) and
`matchCount` is exactly 4 every time.

So **the control a tester would actually target is identifiable, and the 16 failures are UIA
implementation detail.** This is the `ignore` case, and the guide's `ignore` list did not cover
it — added in §4 with this as the worked example, plus the correction that the unlabelled rate
is not reliably optimistic. Labelling this screen right moves its rate by **13.6 %**.

`nearestLabel` is empty on all 16 and cannot be blamed: the nearest `Text`/`Group`/`CheckBox` is
199 physical px away at 120 dpi = **159 DIP**, far past `MAX_LABEL_GAP_DIP` 48. The rule is
declining correctly — a 159-DIP pairing would be a wrong label, not a helpful one. The row's
real name lives on a **`CheckBox`** (`m_cbLockAfterGlobalTime`), and `LABEL_TYPES` is
`{Text, Group}`, so no gap change would reach it either. Not #29's to alter: `nearest_label` is
normative under #11 (healing recomputes it from a stored snapshot), so changing it is an ADR
plus a `FEATURE_VERSION` bump that touches galip's scorer.

**HandBrake's one ambiguous control is a different cause.** Its toolbar has 8 buttons;
7 carry both an `automationId` and a `name`, and `e20` (`siblingIndex` 0) carries **neither**,
no `nearestLabel` either. Its proposal escalates to `{className: Button, parentPath:
Window/Custom/ToolBar}`, which all 8 share → `matchCount` 8. The only property that would
separate it is `siblingIndex`, and `suggestUses` does not escalate to it — deliberately, since
UIA child order is not stable across runs (the same reason playback refuses "the first match",
#40). So this control is **not identifiable by AYNA today**, and that is a real limit to report
rather than a harness bug. Whether a human labels it `control` or `ignore` decides whether the
labelled rate is 97.8 % or 100 %, which is exactly what `labelling.md` exists to adjudicate.

**43 eval tests pass and ruff is clean**, run here on 2026-11-12. The whole measuring half is
covered off Windows; nothing of the capture half has run against a real app yet, so
`UiaDesktop.list_windows()` filtering by `processName` and the multi-window naming are the two
places to watch on the first real run.

## Manual checks

- **PASS** · 2026-11-14 · hasan, on this machine · capture the two KeePass 2 screens
  `kp_state.py` can reach plus HandBrake's main window, then `measure` · result: all three
  captured with 0 read errors and both tables printed; evidence is
  `eval/rq1/snapshots/{keepass2,handbrake}/` and `eval/rq1/results/*-2026-11-14-*.csv`,
  committed in `3c38247`. **It found a real bug** (a screen was being captured as every window
  of the process, double-counting the main form) and two environment facts: `capture` needs
  `agent/.venv`, and `UiaDesktop.list_windows()`'s `processName` filter works as hoped.
- **PASS, 6 of 8 steps as written; the other two were the check's own mistakes** · 2026-11-14 ·
  the user staged the screens on this machine, hasan ran the captures · the eight-step check
  posted on #29 on 2026-11-12
  (https://github.com/galipdg/AYNA/issues/29#issuecomment-6835118882) · display at 125 %
  throughout, Windows 11 Pro 10.0.26300, KeePass 2.61.1, HandBrake 1.11.2.
  - Steps 1, 2, 6, 7 **pass**: `open-database` 19 elements / 216 ms, `options` 87 / 1364 ms,
    `preferences` 74 / 826 ms, `queue` 32 / 236 ms, **all 0 read errors**, each window title the
    intended one and each a single file. Step 2 and step 7 both printed the "N more window(s)
    … skipped" line, which is the `3c38247` topmost-window fix doing its job.
  - Step 4 **superseded**: `main-summary` already existed, so instead of re-capturing it was
    captured under a probe name and diffed — which is how the source-picker staging error was
    found. The probe became the committed `main-summary`.
  - Step 5 **impossible as written**, and not the operator's fault: HandBrake's tabs are all
    `enabled: false` without a source. `main-video` is dropped from `apps.json`.
  - Step 8 **pass**: both tables printed, four CSVs written, and a second `measure` run
    reproduced the CSVs byte-identically (the `47e2485` LF fix).
  - **Two errors in the check text itself, to fix before anyone else runs it:** the interpreter
    must be `agent/.venv/Scripts/python.exe` (the repo-root one fails with
    `cannot load the UIA backend: No module named 'websockets'`), and HandBrake lives at
    `C:\ayna-pilots\handbrake\HandBrake\HandBrake.exe`, one level deeper than the check says.
  - It also asserted the unlabelled rate is the optimistic one. **That is wrong** and is
    corrected in `labelling.md` and the README: the denominator is wrong in both directions.
- **PASS** · 2026-11-14 · the user, on this machine · the `missing` sweep of `labelling.md` §4
  on HandBrake `queue` and KeePass 2 Options → Security: walk the screen and name any control
  that no sheet row carries · result: **nothing missing on either screen**, and the user
  correctly excluded the title-bar close button, which `measure.py` drops anyway. So the
  denominator of both labelled screens is the walk's own output, and the 66.7 % / 100 % rates
  are not inflated by a missed control.
- **(pending)** · hasan + a second labeller · label the report's screen **twice and
  independently** (`labelling.md` §1). Today's two label files are one labeller's work with the
  user confirming the `missing` sweep, which is enough for a first number but not for #64's
  reported one. The judgement calls a second labeller should disagree with, if they are going
  to: `e20` → `ignore` (no bounds, disabled), the three scroll-bar parts of `options` →
  `ignore`, `options` `e1` → `control` (its `automationId` is `m_tbSearch` but its UIA `name`
  is a neighbouring label's text), and HandBrake's six disabled tab items, which are controls
  on a screen where they cannot be clicked.

## Open issues

- **RQ1 does not measure container controls, and that makes the rate pessimistic, not
  optimistic.** `INTERACTIVE_TYPES` is #6's 15-type set, deliberately identical so these
  numbers sit beside the D1 table — but it has `ListItem` and `DataItem` and **not** `List`,
  `Table`, `DataGrid` or `Tree`. Step schema v0.2 targets exactly those containers with
  `rowCount`, `rowExists`, `cell` and `SelectRow`, so HandBrake's `queueJobs` list and
  KeePass 2's `m_lvEntries` are real test targets that never reach the sheet. Both carry an
  `automationId` and would be recognised, so leaving them out **lowers** the measured rate.
  Not labelled `missing` either: `missing` means never recognised, which would be false here.
  Changing the set breaks comparability with #6, so it needs a decision rather than an edit —
  the cheapest honest fix is a second set, counted and reported separately.
- **`measure --labels` prints an app total that mixes labelled and unlabelled screens.** The
  heading says `ground truth, 1/4 screen(s) labelled`, which is true but invites the exact
  misreading this note warns about: KeePass 2's app line reads 99 controls / 100 % while only
  `options` is labelled, and the other three screens contribute raw walk output. **The unit of
  a ground-truth rate is the labelled screen**, and the harness prints no per-screen rate — the
  numbers below were computed from the controls CSV by hand. Worth a `--by-screen` table before
  #64 quotes anything.

- **Three copies of "the primary property set".** `client/src/shared/repository.ts`
  (`IDENTIFYING_FIELDS` + `suggestUses`, escalating, what ships), `agent/ayna_agent/model.py`
  (`PRIMARY_PRIORITY` + `primary_property()`, a single property, unused) and now this harness,
  which imports the agent's constant and appends `control_type` to reach the client's priority.
  They agree today only because I checked. Worth one issue: make one of them normative and have
  the others derive from or test against it. Not in #29's scope.
- `eval/pyproject.toml`'s `testpaths` is `apps/trial/tests` only, so a new test directory is
  invisible to CI until it is added. Adding `rq1/tests` here; the next experiment folder will
  hit the same thing.
- **`ayna_agent.rpc` makes `websockets` a dependency of the recognition backend**, which needs
  nothing from it: `recognition/uia.py` takes four exception types from it and `rpc.py:30`
  imports `websockets.asyncio.server` at module level. `capture` therefore runs on
  `agent/.venv`, not the repo-root one. Requested in galip's inbox 2026-11-14 (move the
  exceptions to a dependency-free module, re-export from `rpc.py`); `rpc.py` is his file, so
  not touched here.
- **`siblingIndex` is the only property that could identify a nameless sibling**, and the
  client's `suggestUses` does not escalate to it. HandBrake's toolbar gives the first real
  example (see "First numbers"). Not #29's to decide — it is a question for `suggestUses`
  (omer) and #40/#11, and it belongs in #64's report either way.

## Decisions taken while building it

- 2026-11-12 — **`by` prefix on the rate CSV's property columns** — `byControlType` and
  `controlType` would otherwise be the same column name, and the row label silently lost to the
  counter. Caught by a test; the test stayed.
- 2026-11-12 — **`sys.stdout.reconfigure("utf-8")`** — the summary is a markdown table meant to
  be pasted into an issue and it carries Turkish control names; this console is cp1254 and
  turned the em dash into `?` before the fix.
- 2026-11-12 — **The label file is separate from the controls CSV, not a column in it** — the
  sheet is regenerated on every `measure` run, so a human's work cannot live in it.
- 2026-11-12 — **`conftest.py` adds `agent/` to `sys.path`, not just `measure.py`** — ruff sorts
  a test module's imports, and `from ayna_agent...` sorted *above* `import measure`, so the path
  could not depend on `measure` being imported first. It failed exactly that way once.

## Handoff

The `sys.path` insert at the top of `measure.py` is load-bearing and intentional: `eval/` has no
packages (`[tool.setuptools] packages = []`) and the agent is not an `eval` dependency, so the
import is by repository layout. If `agent/ayna_agent/model.py` or `playback/resolve.py` ever grow
a pywinauto import, this harness stops working off Windows and the CI test goes with it — both
modules say in their docstrings that they must not, and a test here pins it.

## Why the PR does not close the issue

PR #233 deliberately omits `Closes #29`: none of the three criteria is met, since all three need
the pilot apps measured here. It is up for review anyway because the *definition* of "recognised"
is what is worth agreeing before any number exists — galip wrote the SDD §6.1 sentence this makes
exact and omer owns `suggestUses`, the rule being measured. Two questions are put to them in the
PR body: whether the report also wants the single-property rate for comparison, and whether to
open an issue making one of the three primary-set descriptions normative.

## Outcome (fill when the issue closes)
