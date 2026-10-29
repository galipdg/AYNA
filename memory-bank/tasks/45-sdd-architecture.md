# #45 SDD: architecture and data-model sections

- Issue: https://github.com/galipdg/AYNA/issues/45
- Owner: omer · Branch: `omer/45-sdd-architecture`
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
`docs/sdd/SDD.md` with the whole skeleton (IEEE 1016-2009 style, like the RS follows 29148) and sections 1–4 written: introduction, architecture (context, components with dependency rules and main flows, deployment, cross-cutting), data design (graph model v0 summary + changes planned before the G1 freeze), interface design (contracts table, REST endpoint list, versioning). Sections 5–8 are placeholders naming their issue. Status labels Built / Planned / Proposed as in galip's `SDD-ai.md`; cross-references by path, issue and requirement ID. Sources: `memory-bank/project/architecture.md`, `docs/graph-model.md`, `docs/rs/scenarios.md`, contracts on open PRs (#135 agent RPC, #146 `ai/API.md`, #151 proposal transport, #150 step schema 0.2).

## Decisions (small, local to this task)
- 2026-10-29 — IEEE 1016-2009 structure (omer's choice): consistent with the RS's 29148; issue's "sections 1–4" = intro, architecture, data, interfaces.
- 2026-10-29 — galip's AI block goes in as one section (§5), moved unchanged at #53 with headings renumbered AI-n → 5.n (omer's choice; answer to galip's #50 inbox question, sent to his inbox).
- 2026-10-29 — `docs/graph-model.md` stays the contract; the SDD summarises it and links to it instead of copying the sample queries.

## Status
- [x] Skeleton + sections 1–4 drafted
- [ ] PR with review by one other member (galip suggested: he wrote the AI sections and owns the contracts on #135/#146/#151)
- Next step: ask omer to push and open the PR (`Closes #45`), review requested from galip; then render the Mermaid diagrams on GitHub and fix any that fail.

## Manual checks
- pending · Mermaid diagrams (6) render on GitHub — no local renderer here, not checked

## Open issues
- Found while writing (listed in SDD §9): no Application → RepoObject / TestCase links in graph v0 (#25, #39); FR-07 says names unique per application, the #134 review said per application version (#25); no common REST error body, Spring's default leaves out the message, needed for NFR-15 (#31, RFC 9457 proposed); nginx in `architecture.md` has no designed role.
- #148 and #152 look like duplicates (both "server load test for NFR-07/NFR-08"); suggest closing one.
- Several statuses depend on open PRs (#134, #135, #142, #146, #150, #151, #154); re-check §2.2 and §4.1 when they merge.

## Handoff
- At #53: move `SDD-ai.md` into §5, write §7 from the ADR index and §8 from the final RS; render diagrams for the PDF; align reference numbers with the RS and `docs/literature.md`.

## Outcome (fill when the issue closes)
