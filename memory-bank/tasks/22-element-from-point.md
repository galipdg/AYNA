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
- [ ] Criterion 3 (100 % and 150 % scaling) — **not ticked**: see Manual checks.
- [x] Inbox notes, memory, PR #227 (`Closes #22`)
- Next step: wait for omer's re-review of #227. Then criterion 3 (the scaling check below) and,
  if #224 merges first, `$defs/elementFromPointRequest` / `elementFromPointResult` here as 1.1.

## Manual checks
- **Pending — criterion 3, display scaling.** I cannot tick this from a test run: changing the
  display scaling needs a person at the machine, and this machine sits at **125 % (120 DPI)**, so
  neither of the two scalings the criterion names has been exercised. The code path itself has no
  scaling arithmetic — the process is per-monitor-v2 aware (#201) and the point is passed through
  untouched — so what the check proves is that the client and the agent agree about the point,
  not that this module converts correctly.

  **Setup.** Start the trial app from the repository root with its own interpreter:
  `.venv/Scripts/python.exe eval/apps/trial/app.py`. Nothing else is needed - the test
  brings the window to the front itself.
  **Steps.**
  1. Windows Settings → Display → Scale **100 %**, sign out and in if Windows asks.
  2. `cd agent && .venv/Scripts/python.exe -m pytest tests/test_uia_element_from_point.py -q`
  3. Set the scale to **150 %**, sign out and in, and run the same command.
  4. Set the scale back to 125 %.
  **Expected.** 19 passed both times. The two Windows tests are the ones that matter:
  `test_a_leaf_of_the_trial_app_is_found_exactly_at_its_centre` and
  `test_a_container_answers_with_something_inside_itself`.
  **Report back.** Pass/fail per scaling. On a failure: the full pytest output, the
  `window dpi=` line the snapshot reports, and the Windows build.

  Worth running the same two scalings again end to end once omer's pick hotkey is wired up
  (#184 step 8), because that is the half that converts DIP to physical pixels.

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
