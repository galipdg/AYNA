# Neo4j as the single database

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
The UI is a tree, tests reference its elements, and self-healing and change-impact analysis need neighbourhood and hierarchy queries. Retrieval for the NL assistant needs vector search.

## Decision
Neo4j Community Edition is the only database: repository, snapshots, tests, runs, healing proposals and embeddings (vector index). Screenshots are files on the server disk; the graph stores paths. No PostgreSQL/pgvector.

## Consequences
One store to operate. The team must learn Cypher and Spring Data Neo4j; the graph schema is frozen at G1 and changed only by migration + ADR.
