# Graph schema v0.4: one Window per snapshot id

- Date: 2026-11-07
- Status: Proposed (asked for by Hasan and Galip in the #182 review; their approval on #182 accepts it)
- Deciders: Ömerfaruk (proposal), Galip, Hasan
- Issue: #15 (also used by #30, #51, #61)

## Context
The snapshot import (#15, PR #182) stores one `Window` per snapshot id and treats a repeat of the id as a no-op (FR-04). The check ran in the write transaction with no constraint behind it, so two overlapping imports of one new id could both create a Window. After that, `SnapshotService.response()` (`.single()`) fails for every later import or read of that snapshot. The retry path that makes this likely is by design: #61's outbox repeats `PUT /api/runs/{runId}/results/{stepIndex}` after a timeout, and #51 imports a `repairProposed` result's snapshot inside that write. Without an index on `Window.snapshotId`, the import, its response and #30's repository list (once per object) also scan every Window.

The import also dropped the capture block's evidence: `durationMs` (NFR-02), `readErrors` and `agentVersion`, which RQ1 (#64) needs to tell "AYNA did not recognise this control" from "a property read failed during that walk".

## Options considered
1. **Uniqueness constraint on `Window.snapshotId`** (`V0005`): the loser of a race gets `ConstraintValidationFailed` and runs again as a repeat, the same pattern as `step_result_key` in `V0004` (#44). The constraint is also the index.
2. **A plain index and a lock** (e.g. `MERGE` on a lock node): the index fixes the scans, but the race needs extra code and a second node type.
3. **Leave it to #61** to avoid overlapping retries: the client cannot know whether a timed-out write committed, so it cannot avoid them.

## Decision
Option 1, in migration `V0005` (`V0004` is #44's):
- `CREATE CONSTRAINT window_snapshot_id FOR (n:Window) REQUIRE n.snapshotId IS UNIQUE`. A snapshot id is unique across all versions, as the import already required (the same id under another version is a 409).
- `SnapshotService.importSnapshot` runs the write again once on `ConstraintValidationFailed`; the second run finds the first import and answers 200 (or 409 for another version). `importInto` (the caller's transaction, #51) lets the exception through, and the caller repeats its whole write, as `RunService.writeResult` does.
- New Window properties: `captureDurationMs` (`capture.durationMs`), `readErrors` and `agentVersion` (both optional in the snapshot schema, stored when present). `window.bounds`, `window.dpi` and `capture.budgetMs` stay out on purpose.

## Consequences
- Every Window carries `snapshotId` today (the import is its only writer); a future writer of Windows without a snapshot is not affected, because a uniqueness constraint ignores nodes without the property.
- A development database that already holds two Windows with one snapshot id makes `V0005` fail at start-up; delete the duplicate (or `docker compose down -v`).
- #64 can read the capture's duration, read errors and agent version from the stored Window instead of capturing again.
