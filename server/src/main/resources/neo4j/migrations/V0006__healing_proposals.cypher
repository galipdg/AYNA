// Graph schema v0.7 (#74, ADRs 2026-10-28 healing-proposal-transport and 2026-10-31 healing-proposal-schema-0-2).
// Model: docs/graph-model.md. New relationships: (StepResult)-[:PROPOSED]->(HealingProposal) and
// (Rule)-[:FOR]->(RepoObject); per-candidate data moves onto CANDIDATE {rank, score, scoreExact,
// properties, contributions, similarities}. Relationships and properties need no migration; these
// indexes serve the proposal list (GET /api/healing/proposals), filtered by status, newest first.
CREATE INDEX healing_proposal_status IF NOT EXISTS FOR (n:HealingProposal) ON (n.status);
CREATE INDEX healing_proposal_created_at IF NOT EXISTS FOR (n:HealingProposal) ON (n.createdAt);
