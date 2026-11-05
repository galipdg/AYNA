// Graph schema v0.2 (#60, ADR 2026-10-31 accounts-and-tokens). Model: docs/graph-model.md.
// New relationship: (User)-[:HAS_TOKEN]->(AuthToken), sessions and CI API tokens.
// New TestCase properties: createdBy, createdAt, updatedBy, updatedAt (user id, datetime).

CREATE CONSTRAINT user_id IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE;
// Stored lower-case, so this is case-insensitive uniqueness. Removed accounts keep their name.
CREATE CONSTRAINT user_username IF NOT EXISTS FOR (n:User) REQUIRE n.username IS UNIQUE;
CREATE CONSTRAINT auth_token_id IF NOT EXISTS FOR (n:AuthToken) REQUIRE n.id IS UNIQUE;
// Every request looks its token up by hash.
CREATE CONSTRAINT auth_token_hash IF NOT EXISTS FOR (n:AuthToken) REQUIRE n.tokenHash IS UNIQUE;
