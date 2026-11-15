# #46 Controlled UI-change versions of the sample app

- Issue: https://github.com/galipdg/AYNA/issues/46
- Owner: hasan · Branch: `hasan/46-ui-change-versions`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach
Six change versions of the #33 sample app (`v2a` … `v2f`), one change *kind* each plus one
combined, with a ground-truth mapping old element -> new element for every control they touch.

**Not six copies of the app.** The issue's "Expected output" says `eval/apps/sample/v2a..v2f`,
i.e. six directories. Agreed with the user on 2026-11-15 to ship **one variant layer** instead:

- `variants.py` — the change sets, declarative and Qt-free, so the spec is testable anywhere.
- `variant_patch.py` — applies a change set to a built window (Qt), and **reports every widget
  it touched**, which is what the ground truth is generated from.
- `ground_truth.py` — builds each screen twice (v1 and the variant) on Qt's offscreen platform
  and writes `ground_truth.json` from the two widget trees. Never typed by hand.
- `variants.md` — the change log (criterion 3), one table per version.
- `sample_app.py --variant v2a`, `uia_check.py --variant v2a`.

Three reasons, in the order they decided it:
1. **The ground truth cannot drift.** Generated from the same declaration the app applies, so a
   change that is in the app is in the mapping and vice versa; six copies would be two sources.
2. `eval/AGENTS.md`'s "one module name per tree" has no exception for scripts (#199), so six
   copies of `windows.py`/`model.py`/`texts.py` would each need unique names -- 7 copies of
   ~1800 lines, and a fix in `model.py` edited in seven places.
3. A reviewer reads the change set, not a diff of six trees: the declaration *is* the change log.

Scope: the three screens the reference scenarios and the healing measurement actually cross --
`login`, `main` (grid), `detail`. Settings and the wizard are untouched on purpose.

The hook is in each window's `__init__` (`variant_patch.apply_active(self)`), not in
`sample_app.py`: a screen opens the next one itself, so a run that logs in has to reach the
*changed* customer list. Untouched windows still get the version in their title.

## Decisions (small, local to this task)
- 2026-11-15 — One variant layer instead of six directories (above), user's call.
- 2026-11-15 — Variant strings live in `variants.py` next to the change, not in `texts.py`, so a
  change's old -> new pair is readable in one place. `texts.py` keeps every *v1* string.
- 2026-11-15 — **A retype only ever becomes a class whose API covers what the app calls on the
  control**, and the patch **rebinds the window's attribute** to the new widget. Otherwise
  `self.result_count_label.setText(...)` would call into a deleted C++ object and kill the
  process. `notesInput` (`toPlainText`), the check boxes (`isChecked`) and the city combo boxes
  (`currentText`) are therefore never retyped; the five that are, are only ever `setText` or
  never read at all.
- 2026-11-15 — A removal unbinds the attribute first (to `None`), so a later call raises in
  Python instead of crashing. Only `main.wizardButton` is removed, and nothing calls it.
- 2026-11-15 — The ground truth records the **layout** place (`layoutIndex`, `cell`), not a UIA
  sibling index: only a real provider can report tree order, and the retype deviation below is
  exactly why claiming it would have been wrong.
- 2026-11-15 — The mapping includes rows for controls nobody declared: a form row drags its
  label (`kind` of the declared change, `declared: false`) and a row that leaves a form pushes
  its neighbours (`kind: "shifted"`). So "a mapping for every changed control" means every
  control whose *description* changed, which is what `test_every_changed_control_is_in_the_mapping`
  diffs on the screen itself rather than reading off the spec.
- 2026-11-15 — `uia_check.kill_process_tree` now waits for the process. Not cosmetic: `taskkill`
  returns before the window leaves the UIA tree, and the next test looking for the same
  ClassName found two windows.

## Status
- [x] Branch, task note, #46 In progress on the Project
- [x] `variants.py` (6 versions, 35 declared changes), `variant_patch.py`, `ground_truth.py`
- [x] `ground_truth.json` generated (48 mapping rows, 35 declared + 13 dragged along), `variants.md` change log
- [x] `--variant` on `sample_app.py` and `uia_check.py`, hook in all six windows
- [x] `tests/test_variants.py` (26, offscreen) and `tests/test_variant_uia.py` (23, Windows)
- [x] Windows run: **23 of 23 pass**, after the four corrections under "Manual checks"
- [x] All three acceptance criteria met (≥5 versions, a mapping for every changed control, a
      change log describing each change), each with a test that checks it
- [x] Committed (`478630e`), pushed, **PR #238** open with both reviews requested and the
      issue's three criteria ticked; all five CI jobs pass, including `eval` on the Windows
      runner (1m28s), so the 23 UIA tests run in CI too
- Next step: nothing of mine. It waits on the two reviews and then on a merge. #47's branch is
  stacked on this one (PR #239) and gets retargeted to `main` when this merges.

## Manual checks
- 2026-11-15 · hasan · `pytest eval/apps/sample/tests/test_variant_uia.py` (17 app launches,
  every row of `ground_truth.json` against a real provider) · **pass, 23 of 23** · evidence:
  this session; the measured facts are in `variants.md` ("Measured on Windows").
  **Four corrections, three of which changed the mapping:**
  1. **A cleared `objectName` does not remove the AutomationId -- Qt substitutes the class
     name**: `login.loginButton` -> `QApplication.login.QPushButton`. Measured for
     `QPushButton`, `QLineEdit` and `QTableWidget` on all three screens. So v2e does **not**
     break #33's second criterion: `uia_check --variant v2e` still passes, while no scenario's
     locator does. `ground_truth.automation_id` models the fallback now.
  2. **A grid's inner UIA elements inherit the grid's AutomationId** (Pane + four Headers), so
     an unfiltered lookup by id finds six elements. `is_app_widget` is the filter, as in v1.
  3. A `QGroupBox` is a `Group` and the re-parented controls hang below it with the longer id —
     the one prediction that was right.
  4. A bug of this layer: a replacement widget got `setVisible(old.isVisible())`, which is
     `False` for every widget of a window not yet shown, so v2c's retyped controls were hidden
     for good and absent from the tree. `isHidden()` now.
- 2026-11-15 · hasan · full suites · `pytest eval` **211 pass**, `cd eval; pytest -q` **155
  pass**, `pytest eval/apps/sample/tests` **106 pass**, ruff check + format clean.
- 2026-11-15 · hasan · two **flaky** UIA tests seen once each and green on re-run:
  `test_leaving_an_edited_form_opens_a_modal_dialog_of_its_own[detail]` and a `detail` case that
  found two `DetailWindow`s (the kill-and-reap race, now fixed). Recorded in the app README as
  data for #69 rather than re-run away.

## Open issues
- **A retyped control moves to the end of its parent's UIA tree order**, because the
  replacement widget is created last and Qt's tree follows child order, not layout order. A
  real re-release would keep it in place. Nothing measures tree order (the mapping records
  `layoutIndex`), but a healer scored on "nth child" would see a change v2c does not declare.
  Qt offers no supported way to reorder a parent's children, so this is documented, not fixed.
- **The id collision of v2e is reasoned, not measured**: no screen has two same-class siblings
  that both lose their id, so "they would share one AutomationId" follows from the fallback rule
  rather than from a dump. One more change version could measure it if #86 needs the case.
- `eval/spikes/` is still excluded from ruff and has no CI job (noted on #23 as well) -- worth
  one issue together with `eval/pyproject.toml`'s `testpaths`.
- #47 (bug-injected versions) can reuse this layer as-is: a `bugs.py` beside `variants.py` with
  the same `apply`/report shape. Worth saying so in #47's first session instead of re-deriving.

## Handoff
What is not obvious from the code:

- **`ground_truth.json` is generated, never edited** (`ground_truth.py --write`), and
  `--check` fails if it is stale; `test_ground_truth_json_is_what_the_generator_writes` is the
  same check in the suite. `eval/AGENTS.md`'s rule about ground-truth files applies from the
  moment an experiment uses it: after that, regenerate only with a new version id.
- **The mapping is certain, the property values are derived.** The old -> new pairing is what
  the patch reports it did; the `name`/`controlType`/`automationId` on each side come from this
  app's three measured Qt -> UIA rules -- and `tests/test_variant_uia.py` is what keeps that
  derivation honest. It has already corrected it once (above).
- **Two windows must stay alive while the ground truth is read.** A window that goes out of
  scope takes its C++ children with it, and the patch's report holds nothing but children;
  `mappings_for` keeps both copies in locals for exactly that reason.
- The Windows test costs **17 app launches** (~28 s). The title check is folded into the main
  test rather than being its own case, which would have doubled that.

## Outcome (fill when the issue closes)
