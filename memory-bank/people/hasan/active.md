# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-15 (Week 6's pair: #46 and #47 both delivered and out).
  **This copy carries #46 and #47 and nothing is newer than it**: it was written on
  `hasan/47-bug-injected-versions`, which is stacked on `hasan/46-ui-change-versions`, which has
  `origin/main` merged as of `6fd87a9`. Three other copies are still behind and each holds its
  own issue's section: `hasan/40-playback-v1` (#40), `hasan/162-windows-llm-latency` (#162) and
  `hasan/23-win32-fallback` (#23). **Whichever merges last keeps every branch's own section** --
  never resolve this file by taking one side.
- Current issue: **none in progress.** Five PRs of mine are open and every one of them waits on
  reviews, not on me: **#238 (#46)**, **#239 (#47, stacked on #238)**, **#237 (#40)**,
  **#236 (#23)**, **#235 (#162)**.
- **The next issue to pick is in Week 7/8 (#54, #55, #61, #62), not #46/#47**: both of Week 6's
  eval issues are done. My review queue was empty on 2026-11-15 -- check it again at session
  start, and read the body of each listed PR.

## #46 and #47 -- the sample app's change and bug versions (2026-11-15)

Both shipped as **one layer each inside `eval/apps/sample/`, not as the directories the issues
asked for** (the user agreed on 2026-11-15, and both PR bodies say so): `variants.py` +
`variant_patch.py` + `ground_truth.py` + `ground_truth.json` + `variants.md` for #46, and
`bugs.py` + `bug_patch.py` + `bugs.md` for #47. Reasons, in the order they decided it: the
ground truth cannot drift from the app when both come from one declaration; `eval/AGENTS.md`
allows a module name **once** per tree with no exception for scripts (#199), so six or five
copies of `windows.py`/`model.py`/`texts.py` would each need unique names; and a reviewer can
read a change set, while nobody reads a diff of six trees.

**The measured finding worth carrying into #73 and the client:** clearing a Qt widget's
`objectName` does **not** remove its AutomationId -- Qt substitutes the class name, so
`login.loginButton` becomes `QApplication.login.QPushButton`. Measured for `QPushButton`,
`QLineEdit` and `QTableWidget` on three screens. Consequences: `uia_check --variant v2e` still
**passes** #33's "an AutomationId on every control" while no scenario's locator survives; the id
is no longer the logical name; and two same-class siblings that both lose their name would
collide (that last part is reasoned, not measured). A healer matching on `automationId` will see
a plausible-looking id that means nothing. In galip's inbox and in `learnings.md`.

Three more things the next session should not re-derive:

- **A grid's inner UIA elements inherit the grid's AutomationId** (Pane + four Headers), so a
  lookup by id finds six elements unless it filters with `uia_check.is_app_widget`.
- **A Qt signal keeps calling the method that existed when `connect` ran**, which is why #47's
  bugs patch module globals and *class* methods before the first window exists, while #46's UI
  changes use a per-window hook at the end of each `__init__`. Two layers, two shapes, one
  reason.
- **A window kept only in a temporary takes its C++ children with it**: both the ground-truth
  generator and #47's symptom probes hold each window in a local until they have read it.

Numbers, all run on this machine on 2026-11-15: `pytest eval` **241**, the CI invocation
(`cd eval; pytest -q`) **185**, the sample app's own suite **136**, ruff clean. #46's Windows
file is **23 tests / 17 app launches** and #47's is **5 / 5**. #238's five CI jobs all pass.

**What neither issue proves, and must not be claimed:** that a correct AYNA test catches these
bugs, or that a healer repairs these changes. That needs #62 (scenarios in the editor), #54/#55
(played by the agent) and #63 (triage); `bugs.md`'s last section and both task notes say so.

## What is waiting on someone else

- **PR #238 (#46)** and **PR #239 (#47)**: both reviews requested from omer and galip. #239's
  base is `hasan/46-ui-change-versions` -- **retarget it with `gh pr edit 239 --base main` once
  #238 merges.**
- **galip owes an answer on where `bug3` belongs** (in his inbox): the plan asks for a "wrong
  saved value" bug and the RS has no scenario for one, so it sits where SC-20 catches it (the
  wizard's summary carries the role instead of the department). Moving it is a one-row change.
- **PR #237 (#40)** waits on two reviews; its Windows check ran on 2026-11-14, 7 of 7.
- **PR #235 (#162)** and **PR #236 (#23)** wait on reviews.
- **#29 is merged and closed but a second independent labeller is still owed** -- the closing was
  a side effect of the Development-panel link, not a judgement that the work is done.
- **The Windows queue's other seven are omer's** (#206, #204, #184, #68, #38, #24, #17) and need
  him present. #24's check is mine to run after his fix to PR #234 (my CHANGES_REQUESTED there:
  `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the Spy captures for 30 s and 120 s).

## Still live from earlier sessions

- **#40 (Playback v1)**: all six keywords, the ready gate, the three row shapes, the read-back
  ladder. `memory-bank/tasks/40-playback-v1.md` has the decisions, and the four defects the
  Windows check found are the lesson -- every one needed a real provider and every one passed
  612 unit tests. Open: `items.write`'s read-back has no grace period, and three branches of
  playback have never met a real provider (the cell-selecting view, a WPF `DataGrid`, an
  editable combo box). The manual `runSteps` driver stays inside #61's scope.
- **#162**: a 60 s Windows deadline, not 30; `gemma4:e4b-it-qat` fits 6 GB VRAM and `qwen3:8b`
  does not, so gemma4 is 3.2x faster *here* -- "which model is faster" is a question about the
  box. Output is **not** reproducible at temperature 0 with seed 42 (matters for RQ3, #77).
- **#23**: the win32 fallback is answered and deliberately not built. One genuine finding: a
  native Win32 `Edit` kept control id 1001 across a restart, which `_GENERATED_ID` throws away.
  Sample size one; it needs an ADR and a `FEATURE_VERSION` bump, so it is an open issue, not a
  change.
- **#29**: the first labelled rates, per screen, are the only quotable ones -- HandBrake `queue`
  **4/6 = 66.7 %**, KeePass 2 `options` **35/35 = 100 %**. Never quote the app totals, because
  `measure --labels` mixes labelled and unlabelled screens.
- **Four inbox items are still live**: (1) add `ayna_cli*` to `agent/pyproject.toml`'s packages
  when #61 starts; (2) galip's four Qt measurements from #147; (3) build
  `eval/nl/objects/sample.json` from `uia_check.py --json`, plus my §8 points for #57; (4)
  confirm for #67 that playback needs an unlocked interactive desktop, and settle TBD-3 (Windows
  versions, LTSC) with omer. The #10 literature entries are **done** (PR #171, 31 October).

## Machine and tooling facts that keep costing time

- **`capture` and anything importing the recognition backend run on `agent/.venv`**, not the
  repo-root one (`recognition/uia.py` -> `ayna_agent.rpc` -> `websockets`). The sample app and
  everything under `eval/` run on the **root** `.venv`, the only one with PySide6.
- **`pytest eval` is not the run CI does.** Reproduce CI with
  `cd eval; ../.venv/Scripts/python.exe -m pytest -q` before pushing anything that adds a module
  under `eval/`.
- **The Project status needs `--hostname`**: `gh auth refresh --hostname github.com --scopes
  project`. The option ids and the `item-edit` command are in
  `memory-bank/project/conventions.md`.
- **Leave no UIA-driven app open while the `eval` suite runs**, and expect the occasional flake:
  two were seen on 2026-11-15 (a modal dialog not yet in the tree; two `DetailWindow`s because a
  killed app had not been reaped -- `kill_process_tree` waits for it now). Both are #69 data.
- **Merging a PR is the agent's prohibition, not the user's.** An approved PR of mine is the
  user's to merge whenever they want -- do not tell them it is waiting on omer.
