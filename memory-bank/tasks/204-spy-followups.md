# #204 Object Spy: capture budget, search noise and large trees

- Issue: https://github.com/galipdg/AYNA/issues/204
- Owner: omer · Branch: `omer/204-spy-followups`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
Eight review points on the Spy (#186, #188, #189 reviews; hasan's #184 Windows run). Points 1–3 are
main-process / dev-mock changes testable with `node --test`; 4, 5, 7 are renderer + `shared/tree.ts`;
6 needs a cost found on macOS and a measurement on Windows.

## Decisions (small, local to this task)
- 2026-11-08 — budget ladder stops at 120 s, not the agent's 600 s maximum: the Spy has no
  cancel button while capturing, and the issue asked for 30 s as the second try. KeePass 2's
  278.5 s (#161) would still fail; revisit if the Windows session shows a real window between.
- 2026-11-08 — point 3: read the real file rather than a byte-identity test; `--snapshot <file>`
  still lets anyone try an edited tree.
- 2026-11-08 — PRs #217 (#207) and #218 (#203) are open and touch `i18n/en.ts`, `tr.ts`,
  `docs/ui/style-guide.md`, `dev/demo/seed.mjs`: new strings go in new lines, not rewrites of
  lines those PRs change, to keep the merge clean.

## Status
- [x] 1 capture budget after a timeout — `nextSnapshotBudget` in `shared/snapshot.ts`: 5 s (agent
  default) → 30 s → 120 s; a window keeps the budget it needed for its next capture; choosing
  another window resets it. The client waits budget + 10 s (`SNAPSHOT_MARGIN_MS`).
- [x] 2 newer snapshot version → reason `snapshot-version`, detail = the agent's version
- [x] 3 mock reads `schemas/examples/snapshot/trial-login.json`; copy deleted (it differed only in
  Prettier formatting). `--slow-snapshots` now walks 20 s, so a 30 s retry succeeds in `dev:mock`.
- [x] 4 AutomationId search on the leaf (`automationIdLeaf` in `shared/tree.ts`); a query with a
  dot matches the whole id, so a pasted id still works. The tree caption still shows the full id.
- [x] 5 unnamed structural rows: an element with no Name and no AutomationId is captioned by its
  type alone, muted (`.node-unnamed`). Not collapsed: collapsing changes the tree's shape for
  keyboard moves and parent paths, and labelling answers "26 % of rows say nothing".
- [~] 6 large-tree smoothness — cause found on macOS, fix in; **Windows measurement pending**.
  Harness (scratch Vite page rendering `ElementTree` alone, pane hidden so only sizes are
  trustworthy, not frame times): scrolling a 3031-element uniform tree kept **1** canvas width;
  a 285-element Chromium-shaped tree (unnamed wrapper chains to depth ~45, captions of very
  different lengths) went through **12** widths (581–1157 px), because `.tree-canvas` was
  `min-width: max-content` of the rows drawn at that moment, so the horizontal scroll range and
  offset jumped on nearly every step. Now the width is `max(100%, deepest row's indent + 300 px)`
  over all visible rows and a longer caption ends in "…" (full text in `title`): 1 width
  (1136 px) through the same scroll. Search on 285 elements: ~27 ms, not the cost.
- [x] 7 Add to repository opens "Advanced settings" when the suggested Find-by set does not find
  exactly one element; style guide §Advanced reworded (not "only test engineers").
- [ ] 8 (optional) dev-only Desktop behind the real `rpc.py`
- PR #219 open (Part of #204), reviews requested from hasan and galip. Point 8 left to galip.
- Next step: wait for the Windows session result and the reviews; fix what they find on this branch.

## Manual checks
- 2026-11-08 · pending Windows session · steps 1–7 (point 6 on VS Code; 4, 7 on the trial app;
  1 on KeePass 2) · posted on #204 (issuecomment-6725533870), label `needs-windows-test`.

## Open issues
- Deep Chromium trees indent 16 px per level, so a row at depth 45 starts 720 px in; a smaller
  indent past some depth, or scrolling the chosen row's caption into view horizontally, would
  help. Not in #204's points; raise it after the Windows session if it still reads badly.
- **#217 (#207) adds `client/src/main/__tests__/demoSeed.test.ts`, which reads
  `dev/mock/snapshot.json`.** This branch deletes that file. Whichever PR merges second must point
  the test at `schemas/examples/snapshot/trial-login.json` (or `defaultSnapshot`).

## Handoff

## Outcome (fill when the issue closes)
