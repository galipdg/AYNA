# #50 SDD: AI sections

- Issue: https://github.com/galipdg/AYNA/issues/50
- Owner: galip · Branch: `galip/50-sdd-ai-sections`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
Write the AI sections of the SDD as `docs/sdd/SDD-ai.md` (headings `AI-1` … `AI-10`), for omer to fold into `docs/sdd/SDD.md` at #53. Content is the design as built on the open PRs (#134 step schema, #141 healing scorer, #142 constrained generation) plus the planned parts, each marked with its issue (#42, #43, #58, #63, #71, #73–#75, #103). Requirement IDs come from `docs/rs/scenarios.md` (#34, PR #140), which the RS (#35) takes over unchanged; #35's `RS.md` does not exist yet.

## Decisions (small, local to this task)
- 2026-10-27 — Separate file `docs/sdd/SDD-ai.md`, not `SDD.md` (orchestrator decision): `docs/sdd/` is omer's and his skeleton (#45) does not exist yet. Headings `AI-n`, no references to SDD section numbers, a fold-in note at the top; omer asked where it goes (his inbox).
- 2026-10-27 — Every part is labelled **Built** (with the PR that holds the code) or **Planned** (with its issue). Proposals made here for planned parts are labelled "proposed" and name the issue that settles them, so the SDD does not pretend they are decided.
- 2026-10-27 — Design proposals recorded in the SDD for galip's own planned issues: per-step validation and drop list (#71, FR-26 / SC-27), a `reason` field split off before validation (#71, FR-25), a reserved no-match target in the generation enum (#71), a service timeout well below the CLI's 120 s (#71), an AI-service embed endpoint so the server stays the only writer of the graph (#58). Each is open until its issue implements and measures it.
- 2026-10-27 — Literature cited with `docs/literature.md` numbers ([7], [15], [40]–[47]); the numbering is provisional there, so the SDD says it will be aligned at #53.

## Status
- [x] Branch, task note, board → In progress
- [x] `docs/sdd/SDD-ai.md` drafted (AI-1 … AI-10)
- [x] Inbox: omer (fold-in location, graph/compose/RPC questions), hasan (decision-log fields, healing trigger/transport)
- [x] PR https://github.com/galipdg/AYNA/pull/144 opened 2026-10-27 (`Closes #50`, merge after #134, #141, #142); reviewers omerfaruksaribal, HasanBerk18
- [x] Mermaid diagrams render with Mermaid 11.4.1 (local scratch page); GitHub rendering not checked
- [ ] Acceptance "reviewed" — human step, not ticked by the agent
- Next step: address review comments; after #134, #141, #142 merge, check the cited paths and numbers still match the merged code.

## Manual checks
- None (document). Check that the Mermaid diagrams render in the PR's rich diff on GitHub.

## Open issues
- The SDD's open-issues table (AI-9) lists the design gaps found while writing; the ones that need new GitHub issues: step schema v0.2 for table rows (from #37), proposal transport agent → server (not in the RPC contract v0.1, #73/#74/#52), AI service access to Neo4j for retrieval (#58 vs the architecture diagram), loopback-only model client vs a separate Ollama container (#82).
- `docs/literature.md` (PR #139) cites retrieval as "#57"; it is #58 (#57 is the dataset). Fix on the #20 branch.

## Handoff
- When a planned part is built, move it from "Planned" to "Built" in `SDD-ai.md` and update the numbers (latency, recall) in the same PR as the code, until #53 folds the file into `SDD.md`; after that, edit `SDD.md`'s AI sections instead (ask omer).

## Outcome (fill when the issue closes)
