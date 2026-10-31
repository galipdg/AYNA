# #11 Element descriptor v0

- Issue: https://github.com/galipdg/AYNA/issues/11
- Owner: hasan · Branch: `hasan/11-element-descriptor`
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
Define the descriptor twice — as a `schemas/` contract and as a Python model — and keep the
model free of UI Automation: it takes **raw nodes** (plain mappings of already-read properties
plus the tree links) and returns descriptors. That is what lets the rules be unit-tested on any
OS, replayed over the four #6 dumps, and reused by #12 without a second implementation.

The three computed properties (`parentPath`, `siblingIndex`, `nearestLabel`) were designed from
measurement, not from taste: each candidate rule was run over the #6 dumps and the trial app and
judged against UI Automation's own `LabeledBy` relation. The numbers are in the ADR
`2026-10-31-element-descriptor-v0`.

## Decisions (small, local to this task)
- 2026-10-31 — camelCase in JSON, snake_case in Python, `siblingIndex` rather than the issue's
  `index_in_parent`: the scorer and `healing-proposal.schema.json` already use these names, and
  renaming a shipped contract to match an issue's prose would be the wrong way round.
- 2026-10-31 — The descriptor is a **superset** of the proposal's `scoredElement` and a test
  asserts it stays one, so a stored element can always be rebuilt into a scorer input.
- 2026-10-31 — `helpText` and `accessKey` are captured but not scored: #161 measured capture at
  12 ms per element, so a missing property costs a new run while an unused one costs bytes.
- 2026-10-31 — The label rule accepts **only a label to the left**, within **48 DIP**. Both
  numbers come from the data (see Results); a version that also accepted a label above was
  written, measured and discarded.
- 2026-10-31 — `jsonschema` goes into agent's `[dev]` extras rather than putting the element
  schema's tests in `ai/` as the step schema does: the agent is what produces descriptors, so
  the contract test belongs next to the producer.
- 2026-10-31 — The trial app's captured tree is committed as a test fixture
  (`agent/tests/data/trial-app-tree.json`, 14 nodes) so the acceptance criterion "a descriptor
  for every element of the trial app" is checked by CI on every platform, not only by a Windows
  run.

## Status
- [x] `schemas/element.schema.json` v0.1 + named cases in `schemas/examples/element/cases.json`
- [x] `agent/ayna_agent/model.py`: `Element`, `describe_tree`, `parent_path`, `nearest_label`,
      `is_generated_id`, `PRIMARY_PRIORITY`, `NEVER_MATCH`
- [x] `agent/tests/test_model.py` — 53 tests; whole agent suite **171 passed**; ruff check and
      format clean. `jsonschema~=4.26` added to agent's `[dev]` extras (user's decision,
      2026-10-31) so the schema cases and the trial-app descriptors are checked in CI
- [x] Trial app captured on Windows at 125 % scaling: 14 elements, 14 descriptors, 0 read
      errors, all 14 valid against the schema
- [x] ADR `2026-10-31-element-descriptor-v0` (Proposed) + index line
- [ ] PR with `Closes #11`; needs all three approvals because it adds a `schemas/` contract
- Next step: open the PR, then #12 (snapshot export), which emits these descriptors with the
  #161 budget.

## Results that drove the design
- **Only a label to the left.** All 7 KeePassXC elements with a `LabeledBy` relation are
  labelled from the left at 13 DIP; the trial app's two labelled inputs at 6 and 10 DIP.
  Left-first reproduces `LabeledBy` 7/7, distance-first 6/7, and in all 13 cases where the two
  orders differ across the five applications, left-first picks the form label ("User name:",
  "URL:", "Expires:") and distance-first picks a caption or a neighbour ("20 ch.", "Icon:",
  "Tags list").
- **Accepting a label above only mislabels.** It gives the trial app's check box and button the
  password field's label (6 DIP above them) and a KeePass 2 combo box "20 ch.".
- **48 DIP ceiling.** 3.7× the largest true gap, 5.4× below the nearest false pairing (261 DIP).
- **Generated ids.** Whole-string digits, GUIDs, and a Qt dotted id whose leaf is a class name —
  the last is what produced KeePassXC's 10 % id uniqueness (#6 finding 3).

## Manual checks
- 2026-10-31 · hasan · build descriptors for every element of the PySide6 trial app · pass ·
  14/14 with 0 read errors at 125 % scaling; the tree is committed as the test fixture and the
  labels it produces are asserted in `test_model.py`

## Open issues
- **New dev dependency**: `jsonschema~=4.26` in agent's `[dev]` extras, the same version `ai/`
  and `eval/` use. It is only needed to validate the contract in tests; nothing in the product
  path imports it. 15 of 15 named cases behave as named and 14 of 14 trial-app descriptors
  validate.
- **`healing-proposal.schema.json` has no `dpi`** and `additionalProperties: false` on
  `scoredElement`, so a proposal carrying the `dpi` that PR #166 introduces would be invalid.
  galip's file, flagged in the ADR and in the PR.
- **`docs/graph-model.md`'s `Element`** lists six properties; it needs this set, `dpi` included.
  omer's file, already in his inbox from #161.
- `memory-bank/decisions/README.md` is not a `merge=union` file and #169 adds a line at the same
  place, so whichever of the two merges second will conflict there. Keep both lines.

## Handoff
`describe_tree(nodes)` is the whole entry point: give it the #6 dump's `elements` list, or any
list of raw nodes with `id`/`parent`, and it returns descriptors. #12 only has to produce those
raw nodes from UI Automation and add the snapshot's own fields.

## Outcome (fill when the issue closes)
