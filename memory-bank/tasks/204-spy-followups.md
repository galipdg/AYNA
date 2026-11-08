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
- [ ] 4 AutomationId search on the leaf
- [ ] 5 unnamed structural rows
- [ ] 6 large-tree smoothness
- [ ] 7 ambiguous Find-by opens Advanced; style-guide wording
- [ ] 8 (optional) dev-only Desktop behind the real `rpc.py`
- Next step: point 1.

## Manual checks
- (planned) Windows session: point 6 on VS Code (285 elements) — scroll and search; point 1 on
  KeePass 2 (capture again after a timeout).

## Open issues
- **#217 (#207) adds `client/src/main/__tests__/demoSeed.test.ts`, which reads
  `dev/mock/snapshot.json`.** This branch deletes that file. Whichever PR merges second must point
  the test at `schemas/examples/snapshot/trial-login.json` (or `defaultSnapshot`).

## Handoff

## Outcome (fill when the issue closes)
