# #22 Element under cursor + bounds

- Issue: https://github.com/galipdg/AYNA/issues/22
- Owner: hasan · Branch: `hasan/22-element-from-point`
- Started: 2026-11-10 · Last update: 2026-11-12 · PR: #227

## Approach

`elementFromPoint(x, y)` answers **from the snapshot the agent last took of the window under the
point**, instead of deriving a descriptor from the hit element on its own. One UIA hit test
(`IUIAutomation::ElementFromPoint`), one Win32 `WindowFromPoint` + `GetAncestor(GA_ROOT)` for the
top-level handle, then a lookup in the cached document.

Why not derive the descriptor from the element alone: `model.describe_tree` needs the node's
siblings, its parent and the parent's siblings (`nearest_label` rules 2 and 3) and the whole
ancestor chain (`parent_path`). Reading those for one element costs a property read per sibling,
which is unbounded — picking a row in KeePass 2's entry list would read every other row — and,
worse, an element whose siblings were *not* read would come back with `nearestLabel: null`, which
is **indistinguishable from "this element has no label"**. The same element would then have two
different descriptors depending on whether a snapshot happened to be open. Answering from the
snapshot makes the descriptor *the same object* the client is already showing, which is also
exactly what the Spy needs: select the tree node it already has (recorded in `active.md` as the
shape omer can build against).

Reply shape, one shape for every outcome, never an error for a point:

| field | meaning |
|---|---|
| `handle` | top-level window under the point, or `null` when there is no window there |
| `bounds` | the hit element's rectangle, physical pixels, or `null` |
| `snapshotId` | the cached snapshot of that window, or `null` when none is held |
| `elementId` | the element in that snapshot (`"e8"`), or `null` |
| `element` | that snapshot's element descriptor, or `null` |

The three states the client can tell apart:
- `snapshotId` null → nothing captured for this window yet: offer to capture it.
- `snapshotId` set, `elementId` null → the window changed since the capture: offer to capture again.
- both set → select that node.

Matching inside the document: candidates are the elements whose stored `bounds` equal the hit
element's, and **every** candidate — even a single one — is put to `CompareElements` (pywinauto's
`UIAElementInfo.__eq__`). If none compares equal the **last in pre-order** wins, because
same-bounds candidates are a wrapper chain and the deepest is what `ElementFromPoint` returned,
but only when its stored `controlType`, `name` and `automationId` are still the hit element's.
The matching is a pure function over the document (two callbacks carry everything that needs UI
Automation) so it can be tested on macOS.

## Decisions (small, local to this task)

- 2026-11-10 — **The descriptor comes from the cached snapshot, not from a fresh derivation.**
  Reason above: unbounded sibling reads, and a silently weaker `nearestLabel` would make one
  element have two descriptors. Consequence: `elementFromPoint` is only fully useful after a
  `snapshot` of the same window, which is the Spy's actual flow.
- 2026-11-10 — **`snapshot()` keeps the last window's document and live elements** so the lookup
  costs no extra cross-process calls during the walk. One window at a time; a new `snapshot`
  replaces it. Holding the COM pointers is what makes `CompareElements` possible later.
- 2026-11-10 — **A point with nothing under it is not an error.** The reply is the same shape with
  nulls, so the Spy has one code path. Only a host without UI Automation raises (`-32001`).
- 2026-11-10 — **`x` and `y` may be negative.** Virtual-desktop coordinates are signed (a maximised
  window reports `[-11, -11, …]`, `learnings.md` 2026-11-07), so the parameter check is "an int",
  not `_positive_int`.
- 2026-11-12 — **A single candidate is compared too, and the fallback checks three properties**
  (omer's #227 review). The first version let one same-bounds element win with no COM call,
  which is only sound while the window keeps the same elements in the same rectangles. A
  switched tab, a scrolled list and a replaced wizard page all keep the rectangles, so the Spy
  would have selected a stale node silently — worse than state 2, which is what that case is.
  Measured cost: nothing outside the noise (median 2.2 ms / 2.5 ms on two runs of 50, against
  3.39 ms before the change on the same machine). The deepest-candidate fallback stays for the
  raw-view/control-view disagreement, gated on `controlType`, `name` and `automationId`.
- 2026-11-12 — **`model._text` became `model.text_value`** (public), because the live properties
  the identity check reads have to pass through the same normalisation the descriptor stored
  them with. One rule, one function.
- 2026-11-10 — The top-level handle comes from **Win32 `WindowFromPoint` + `GetAncestor(GA_ROOT)`**,
  not from walking UIA parents, so it is the same kind of handle `listWindows` reports
  (`EnumWindows`) and the client can match it to the window it has selected.

## Status
- [x] Task note and branch
- [x] `recognition/uia.py`: `element_from_point`, the snapshot cache, the pure matcher (`d7dcf8c`)
- [x] `rpc.py`: `elementFromPoint` — galip's file, its own commit (`bd74b7e`)
- [x] `docs/agent-rpc.md`: the method — galip's content in my folder, its own commit (`ba86966`)
- [x] Unit tests on the matcher and the reply shape (any OS): 19 + 12
- [x] `@pytest.mark.windows` tests on the trial app, run here: every leaf found at its centre,
      every element answering inside its own subtree, the budget, a point over nothing, an
      uncaptured window. **432 agent tests pass, ruff clean, on Windows 11 at 120 DPI.**
- [x] Criterion 1 **met**: every leaf of the trial window (11 of them, more than the ten asked
      for) answers as itself at the centre of the rectangle the snapshot reports.
- [x] Criterion 2 **met**: with the identity check on, median **2.2 ms**, p95 3.0 ms, worst
      **3.2 ms** over 50 calls (second run 2.5 / 3.7 / 4.2 ms) against the 300 ms budget — about
      100× of headroom. Numbers are in `docs/agent-rpc.md`.
- [x] omer's #227 review answered: identity check on every candidate, the property-gated
      fallback, five new tests, and the doc's "one snapshot" paragraph. **436 agent tests pass
      here, including the Windows ones, ruff clean** — and the real leaf test passes with the
      check on, which answers his question: the hit test and the walk do agree on identity for
      every element of the trial window (all 50 measured calls named one).
- [x] Criterion 3 **met**: the scaling check ran here on 2026-11-12 at **100 %** and at
      **150 %** — 23 tests pass at both, `window dpi` 96 against 144, the window 1.5× larger in
      physical pixels, and the same element id answers every point at both scalings. Details and
      how to repeat it are under Manual checks.
- [x] Inbox notes, memory, PR #227 (`Closes #22`)
- Next step: **all three criteria are met**; the issue's boxes are ticked and the result is a
  comment on #22, with `needs-windows-test` removed. Waiting on omer's re-review of #227 (his
  `CHANGES_REQUESTED` was answered in `142a6c6` on 2026-11-12). If #224 merges first, add
  `$defs/elementFromPointRequest` / `elementFromPointResult` here as 1.1.

## Manual checks
- **Done — criterion 3, display scaling. 2026-11-12, run by hasan with the user at this
  machine. Pass at both scalings.** The user changed the scale in Windows Settings; the agent
  ran the tests and read back what UI Automation reports.

  | Scale | `systemDpi` | `window dpi` | Login window bounds (physical px) | Result |
  |---|---|---|---|---|
  | 100 % | 96 | 96 | `[640, 276, 1000, 440]` — 360 × 164 | 23 passed |
  | 125 % (this machine's own) | 120 | — | — | 23 passed (baseline) |
  | 150 % | 144 | 144 | `[480, 144, 1020, 390]` — 540 × 246 | 23 passed |

  The two scalings really were different for the agent, not only for Windows Settings: the
  window measures 540 × 246 against 360 × 164, **exactly 1.5×**, and every element carries
  `dpi=144` against `dpi=96`. `dpi_awareness()` reported `per-monitor-v2` in both runs.
  At each scaling four points taken at the centre of a snapshot rectangle answered with the
  **same element id** they were taken from (`e4`, `e5`, `e6`, `e8` — three title-bar buttons and
  `usernameInput`), so the hit test and the walk agree on identity at both scalings.
  **436 agent tests pass at 150 %** (13.65 s), and the five `@pytest.mark.windows` tests of this
  module pass at both, including the two that matter:
  `test_a_leaf_of_the_trial_app_is_found_exactly_at_its_centre` and
  `test_a_container_answers_with_something_inside_itself`. Scale set back to 125 % afterwards.

  What this proves and what it does not: the code path has no scaling arithmetic — the process is
  per-monitor-v2 aware (#201) and the point is passed through untouched — so the check shows that
  physical pixels in and physical pixels out stay consistent at both scalings. It does **not**
  cover the client's DIP → physical conversion. Worth running these same two scalings end to end
  once omer's pick hotkey is wired up (#184 step 8), because that is the half that converts.

  **How to repeat it** (the counts below are the current ones; the earlier note said 19, which was
  the test count before `142a6c6` added five):
  **Setup.** Nothing to start — the Windows tests launch the trial app themselves, with the first
  interpreter that can import PySide6 (the repository's root `.venv`), and force its window
  topmost before pointing at it.
  **Steps.**
  1. Windows Settings → Display → Scale **100 %**.
  2. `cd agent && .venv/Scripts/python.exe -m pytest tests/test_uia_element_from_point.py -q`
  3. Set the scale to **150 %** and run the same command.
  4. Set the scale back to 125 %.
  **Expected.** 23 passed both times.
  **Report back.** Pass/fail per scaling. On a failure: the full pytest output, the
  `window dpi=` line the snapshot reports, and the Windows build.

## Open issues
- **`schemas/agent-rpc.schema.json` does not exist on `main` yet** (omer's PR #224, still open,
  waiting on galip). Settled on #227: whichever of the two merges second adds the definitions —
  if #227 goes first, omer puts `elementFromPoint` into #224 as part of 1.0 with no bump; if
  #224 goes first, I add `$defs/elementFromPointRequest` / `elementFromPointResult` here as a
  minor bump to 1.1, every reply field nullable.
- **The `rpcVersion` number is unsettled and it is galip's call.** `runSteps` and
  `elementFromPoint` are built additions to v0.1, so by the contract's own rule they are a minor
  bump, but "v0.2" already names the healing draft in the same file. Under #52 they become 1.1.
  Noted at the top of `docs/agent-rpc.md` and in galip's inbox; `RPC_VERSION` left at `"0.1"`.
- **The agent holds one window's snapshot.** Enough for the Spy (capture, then pick), but if a
  later screen wants to pick across two captured windows this becomes a small cache. Not worth
  building before something needs it.

## Handoff
- The two Windows tests force the trial window topmost on purpose (`_bring_to_front`): a hit test
  answers with what is **visible**, and a terminal running pytest otherwise sits over the app.
  Do not "simplify" that away — it is why the first run failed.
- `match_in_document` is pure: `same_element` and `same_properties` carry everything that needs
  UI Automation, which is what lets the rule be tested on macOS. It makes **one** `CompareElements`
  per candidate and reads three properties only in the fallback. If you ever need to loosen it,
  keep the count bounded by the candidates — that is what makes the call 2 ms instead of 2 000.
- `test_a_window_that_was_never_captured_has_no_snapshot_id` failed once with another window's
  handle: the module fixture raises the trial window only once and it was covered by the last
  test. It now re-raises the window itself. A hit test answers with what is *visible*, so any
  Windows test about a point has to own the stacking order right before it points.

## Outcome (fill when the issue closes)
