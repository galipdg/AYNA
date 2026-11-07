// Graph schema v0.4 (#15, ADR 2026-11-07 window-snapshot-unique). Model: docs/graph-model.md.
// New Window properties: captureDurationMs, readErrors, agentVersion (from the snapshot's capture).

// A snapshot is imported once (FR-04): two overlapping imports of one snapshot id cannot both
// create a Window. The import, its response and the repository list look windows up by it.
CREATE CONSTRAINT window_snapshot_id IF NOT EXISTS FOR (n:Window) REQUIRE n.snapshotId IS UNIQUE;
