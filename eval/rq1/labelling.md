# RQ1 ground-truth labelling guide

**What RQ1 asks:** of the controls a tester would want to automate on a pilot app's screen, how
many can AYNA identify **uniquely** from an element descriptor? (SDD §6.1; issues #29 and #64.)

**Why this guide exists.** `measure.py` can only count elements AYNA's own walk produced. If the
walk never produced a control — a custom-drawn widget, a control behind a virtualised list, a
toolbar that reports nothing — that control silently leaves the denominator and the rate goes
*up*. A rate computed that way measures how good AYNA is at the elements AYNA already found,
which is not the question. So a person enumerates each screen once, and that enumeration is the
denominator.

Labelling is **per snapshot**, not per screen in the abstract: element ids (`e0`, `e1`, …) are
positions in one captured document, so a recapture voids its labels. `measure.py` refuses a
label file whose ids it cannot find, and `eval/AGENTS.md` already forbids editing a ground-truth
file after a result has used it.

---

## 1. Before you start

- Windows machine, the pilot app from `C:\ayna-pilots\`, and the repository root `.venv`.
- Read the app's entry in [`apps.json`](apps.json): it names the process, the screens RQ1
  measures, the state each screen must be in, and how to open it.
- Keep the app at **one display scaling** for the whole session, and write down which. Bounds are
  physical pixels and `dpi` is per element, so a scaling change mid-session is not wrong but it
  makes two snapshots of "the same" screen harder to compare.
- One person captures and labels; a second person reviews §6. Two people labelling the same
  screen independently is better, and is what we do for the screen used in the report.

## 2. Capture

Put the app in the state `apps.json` describes, then, for each screen:

```powershell
.venv/Scripts/python.exe eval/rq1/measure.py capture keepass2 --screen entry-editor
```

It writes `eval/rq1/snapshots/<app>/<screen>.json` and prints the element count, the walk
duration and the read errors. Three things to check before moving on:

- **`readErrors` is 0.** A non-zero count means some properties were not read, so a control may
  look poorer than it is. Note the number in your session log if it will not go away.
- **The element count is plausible** for what you see. A count far below the visible controls is
  itself a finding — record it and carry on; §4's `missing` rows are where it lands.
- **The window title in the file is the window you meant.** With more than one window of the
  process open, the capture writes `<screen>-1.json`, `<screen>-2.json`, … in `listWindows`
  order; rename them or close the others and recapture.

A capture never overwrites: `--force` exists but do not use it on a snapshot a committed result
already used.

## 3. Produce the sheet

```powershell
.venv/Scripts/python.exe eval/rq1/measure.py measure keepass2
```

This writes `eval/rq1/results/<app>-<date>-controls.csv` — one row per control AYNA found, with
its properties, the primary set the Spy would propose, how many elements that set matched, and
two **empty** columns, `label` and `note`. That file is the sheet.

Copy the rows for one screen into `eval/rq1/labels/<app>-<screen>.csv` keeping only three
columns — `elementId,label,note` — and label them. (Keeping the label file small and separate is
what lets the sheet be regenerated at any time without touching a human's work.)

## 4. The three labels

| Label | Meaning | Counts in the denominator? |
|---|---|---|
| `control` | A control a tester would target in a test step: something you click, type into, select, toggle, or check the state of. | **Yes** |
| `ignore` | AYNA listed it, but it is not a control a test targets. | No |
| `missing` | A control **you can see on the screen** that no row in the sheet carries. Leave `elementId` empty and name the control in `note`. | **Yes**, and never recognised |

### What is a `control`

Decide from the screen, not from the descriptor. A control is an element a tester would name in a
step:

- buttons, including the ones in a toolbar and in a dialog's button row;
- text fields, password fields, spin boxes, sliders;
- check boxes and radio buttons;
- combo boxes and the list items a tester selects by text;
- tab items, tree items, menu items that a scenario actually opens;
- a grid's **rows**, where the step schema v0.2 targets a row, not a cell.

### What is `ignore`

- Static text, images, separators, group frames, layout panes — they carry no action. (Most never
  reach the sheet: #6's interactive set already excludes them. A `Document` or `Text` element that
  does reach it is the usual case.)
- The window frame's minimise/maximise/close buttons and its system menu. (Already excluded:
  `measure.py` drops a `TitleBar` and its whole subtree. If one still appears, label it `ignore`
  **and say so in the issue** — the exclusion rule has a hole.)
- An element that duplicates another in the same place because the raw and control views
  disagree. Label the one a tester would not pick `ignore`, and put the other row's `elementId`
  in its `note`.
- **The inner parts of one composite control.** A spinner, a combo box or a date picker reaches
  UIA as several elements, and a tester targets the whole thing, not its pieces. Label the outer
  element `control` and every inner part `ignore`, with the outer row's `elementId` in each
  `note`. *Worked example, KeePass 2 Options → Security, measured 2026-11-14:* each of the four
  rows is one WinForms `NumericUpDown`, and AYNA lists **five** elements for it — the outer
  `Spinner` (`automationId` `m_numLockAfterGlobalTime`, developer-chosen, `control`), an inner
  `Edit` and an inner `Spinner` (both with generated numeric ids) and `Up` / `Down` buttons (no
  id at all) — the last four being `ignore`. The four outer spinners are all recognised; the 16
  inner parts are all ambiguous, because all four composites expose identical names. Getting
  this wrong moves the screen's rate by **13.6 %**, so it is not a detail.
- A menu item inside a menu the reference scenarios never open. Be consistent within an app and
  write the rule you used in §6.
- Rows of a grid that happens to be empty, and placeholder list items.

### What is `missing`

This is the label that makes the number honest, so look for it deliberately:

- walk the screen with the keyboard (Tab, then arrow keys inside each group) and check that every
  stop you reach has a row;
- look at custom-drawn areas — a preview pane, a chart, a drawn toolbar;
- open a long list or grid and check whether rows below the fold have rows in the sheet
  (virtualisation);
- check controls that only appear when enabled, and capture that state as its own screen rather
  than labelling the enabled-only control `missing`.

One `missing` row per control, with a name a teammate would recognise (`"Önizleme panelindeki
oynat düğmesi"`). Turkish is fine in `note`.

## 5. Measure against the ground truth

```powershell
.venv/Scripts/python.exe eval/rq1/measure.py measure keepass2 --labels
```

With `--labels` the denominator is `control` rows + `missing` rows, the `ignore` rows drop out,
and the heading says `ground truth` and how many of the app's screens are labelled. Without
`--labels` it says so too, and **that number is not RQ1's rate and never may be reported as it**.

It is also not reliably the *optimistic* one, which is what this guide used to claim. The
unlabelled denominator is wrong in **both** directions at once, and only labelling separates
them: a control AYNA's walk never found is invisible, which flatters the rate (`missing`), while
every inner part of a composite control is counted as if a tester would target it, which
punishes the rate (`ignore`). KeePass 2's Options → Security measures both at once — see the
`NumericUpDown` example in §4. So do not assume the labelled rate will come out lower.

The CSVs are overwritten per date; the snapshots and labels are what the result is made of.
Commit the snapshot, the label file and both CSVs together.

## 6. Write down the session

In the task note (`memory-bank/tasks/29-rq1-measure.md`, "Manual checks") and in the issue
comment that carries the numbers:

- date, who captured, who labelled, who reviewed;
- app and version, Windows version, display scaling;
- per screen: element count, `readErrors`, how many `control` / `ignore` / `missing`;
- **every judgement call you had to make**, in one line each — which menus you counted, how you
  treated duplicates, anything you were unsure about. The next person has to be able to label
  the same screen the same way, and this list is the only thing that makes that possible.
  Promote a rule you had to invent into §4 of this guide, in the same PR.

## 7. When a label turns out to be wrong

Do not edit a label file a committed result used. Append a new one
(`<app>-<screen>-r2.csv`), say in the task note why it supersedes the first, and report both
numbers once. A ground-truth file that changes quietly makes every earlier number unreadable.
