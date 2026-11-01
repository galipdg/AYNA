# Graph schema v0.1: tests and repository objects belong to an application

- Date: 2026-10-29
- Status: Accepted (Hasan approved the #39 PR #156, Galip on #160, 2026-10-29)
- Deciders: Ömerfaruk (proposal), Galip, Hasan
- Issue: #39 (also used by #25)

## Context
Graph schema v0 (`docs/graph-model.md`, #14) links a `RepoObject` to an application only through `(RepoObject)-[:RESOLVES_TO {version}]->(Element)` and has no link from a `TestCase` to anything above it. The tests API (#39) must list tests per application (NFR-08) and resolve each step's `target` (a logical name) to a repository object of the test's application; the repository API (#25) must keep logical names unique per application (FR-07), including objects not yet resolved in any version. Neo4j properties cannot hold maps, and v0 lists neither `timeoutMs` nor the 0.2 `row` on `Step` (ADR *Step schema v0*, PR #150).

## Options considered
1. **Ownership relationships** `(Application)-[:HAS_TEST]->(TestCase)` and `(Application)-[:HAS_OBJECT]->(RepoObject)`: one hop from the application, same style as `HAS_VERSION`; deleting an application can follow them.
2. **An `appId` property** on `TestCase` and `RepoObject`: no new relationship types, but it duplicates graph structure as a foreign key and is not visible to graph queries such as change impact.
3. **Tests per application version**: a test would have to be copied for every version, which breaks NFR-33 (a UI change needs repository changes only).

## Decision
Option 1, in migration `V0002` (which adds an index on `TestCase.name`; relationships need no schema statement in Neo4j):
- `(Application)-[:HAS_TEST]->(TestCase)`, written by the tests API. Test names are unique per application.
- `(Application)-[:HAS_OBJECT]->(RepoObject)`, written by the repository API (#25). A step's `target` resolves among the objects of its test's application; the server stores only `(Step)-[:TARGETS]->(RepoObject)` and rebuilds `target` from the object's current `name` on read.
- `Step` properties: `keyword`, `value`, `timeoutMs` (integer) as plain properties; `checkpoint` and `row` as JSON strings. `SET s = …` replaces all properties on every save, so a field removed in the editor disappears.

## Consequences
- Logical names are unique per application, as FR-07 says (the #134 review said "per application version"; #25 implements per application).
- Until #25 exists, a test can only target objects created directly in the graph; the integration tests do that.
- The server validates every step write against `schemas/step.schema.json` with networknt json-schema-validator (Apache-2.0, 2020-12, remote fetching off). The build copies the shared file onto the classpath, so the server follows whatever version is on `main`; the server's Docker build context is now the repository root.
- A schema release that adds a structured step field fails `StepSchemaTest` until the server gives it a storage rule.
