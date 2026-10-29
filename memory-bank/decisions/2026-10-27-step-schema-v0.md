# Step schema v0

- Date: 2026-10-27
- Status: Accepted (Ömerfaruk approved the #13 PR #134, 2026-10-29; Hasan approved in a comment on #134, 2026-10-29)
- Deciders: Galip (proposal), Ömerfaruk, Hasan
- Issue: #13

## Context
`schemas/step.schema.json` is the one step format for the editor (#38), the NL assistant (#37, #71), the recorder (#99), the agent's playback (#26, #40), the server and the NL dataset (#36). It is a frozen contract: changing it later means migrating stored tests and every consumer, so v0 should be small and strict. #13 lists the fields `id, keyword, target, value, checkpoint {property, operator, expected}, timeout_ms` and asks for a version field.

## Decision
- **Document, not a bare step.** The root is `{"version": "0.1", "steps": [...]}`. A test, an NL answer or a `runSteps` request carries one version; a single step is `step.schema.json#/$defs/step`. Each schema release accepts only its own `version` (`const`); consumers migrate older documents.
- **Fields of a step:** `id` (optional lower-case UUID, assigned by the server on save, absent on unsaved suggestions), `keyword`, `target`, `value`, `checkpoint`, `timeoutMs`. Nothing else (`additionalProperties: false`), so coordinates or raw UIA properties cannot enter a test.
- **`timeoutMs`, not `timeout_ms`:** every other JSON contract (server DTOs, graph properties, client settings) is camelCase. Integer 0–600000; absent means the run's default.
- **`target` is a logical name** matching `screen.element` in lowerCamelCase ASCII (`^[a-z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*$`, ≤ 100 chars), as in `conventions.md`. The server resolves it to the RepoObject (`(Step)-[:TARGETS]->(RepoObject)`).
- **Per keyword** (enforced with `if`/`then`): Click and Wait take neither `value` nor `checkpoint`; Type needs `value` and replaces the control's text (empty clears it); Select needs a non-empty `value`, the item's text; Verify needs `checkpoint` and no `value`.
- **Wait** waits until the target exists, is visible and enabled, at most `timeoutMs`. There is no fixed sleep. Every step does the same smart wait before acting; Wait is the step that does only that.
- **Checkpoint:** `property` ∈ `name` (UIA Name), `value` (ValuePattern), `enabled`, `visible` (not IsOffscreen), `checked` (TogglePattern On), `selected` (SelectionItem IsSelected); `operator` ∈ `equals`, `notEquals`, `contains`. Text properties take a string `expected` (may be empty) and compare exactly, case-sensitive; boolean properties take a boolean and only `equals`.
- **Bounded strings** (`value`, `expected` ≤ 1000, `target` ≤ 100) so a runaway model output fails early (#7 finding 1).
- **Tests** live in `ai/tests/test_step_schema.py` (Python `jsonschema` 4.26, run by CI's `ai` job) against `schemas/examples/step/`. Other consumers validate with their own JSON Schema 2020-12 library against the same file and examples.

## Options considered
- Version on every step instead of the document: simpler for single-step APIs, but repeated in every step and in the graph.
- Looser `target` (any string, or more than two segments): relaxing later is backward compatible, tightening is not, so v0 starts strict.
- A friendly `text` property (Value if present, else Name): easier for testers, but ambiguous for Qt, where `accessibleName` replaces Name (learnings 2026-10-25). Can be added later without breaking tests.
- Wait with an optional checkpoint ("until the spinner is gone"): useful, but adds playback work now; adding it later is backward compatible.

## Consequences
- The NL assistant generates against a *derived* schema (target as an `enum` of the repository's names, no `if`/`then`, which grammar converters do not support) and then validates the result against this file.
- Neo4j properties cannot hold maps: the server stores `checkpoint` flattened or as a JSON string, and `Step` needs a `timeoutMs` property (`docs/graph-model.md`).
- Playback (#26, #40) implements the semantics above: Type replaces text, the property mapping, exact text comparison.
- Any change bumps `version`, needs a new ADR and updates the examples and every consumer's tests.
