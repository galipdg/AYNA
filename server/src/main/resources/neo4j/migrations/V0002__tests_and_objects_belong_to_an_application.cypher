// Graph schema v0.1 (#39, ADR 2026-10-29 graph-schema-application-links). Model: docs/graph-model.md.
// New relationships (no schema statement needed in Neo4j):
//   (Application)-[:HAS_TEST]->(TestCase)    written by the tests API (#39)
//   (Application)-[:HAS_OBJECT]->(RepoObject) written by the repository API (#25)
// New Step properties: timeoutMs (integer), checkpoint and row (JSON strings).

// Tests are listed by name and names are unique per application.
CREATE INDEX test_case_name IF NOT EXISTS FOR (n:TestCase) ON (n.name);
