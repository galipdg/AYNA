// Graph schema v0.3 (#44, ADR 2026-11-05 runs-api-and-live-updates). Model: docs/graph-model.md.
// New relationship (no schema statement needed in Neo4j):
//   (Run)-[:ON_VERSION]->(AppVersion)  the version a run was played against
// New Run properties: stepCount, document (JSON string), startedBy, finishedAt.
// New StepResult properties: runId, stepIndex, stepId, message, bodyHash, body (JSON string), receivedAt.

// One result per step of a run, so two overlapping retries cannot both create it.
CREATE CONSTRAINT step_result_key IF NOT EXISTS FOR (n:StepResult) REQUIRE (n.runId, n.stepIndex) IS UNIQUE;
