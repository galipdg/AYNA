# docs/ — Course documents, API docs, guides

Owner: hasan; `rs/` and `report/`: galip; `sdd/` and `ui/`: omer (each component owner writes their own SDD section). Read `/AGENTS.md` first; this file adds only what is specific to `docs/`.

## Layout
- Folders: `rs/` (galip), `sdd/` (omer), `api/` (generated, never hand-edited)
- Single documents, all hasan's, each named by the issue that asked for it:
  `graph-model.md` (#14), `tool-matrix.md` (#18), `agent-rpc.md` (#16),
  `working-agreement.md` (#8), `requirements-workshop.md` (#19)
- Not here yet, listed so they land in the right place: `ui/` (omer, the client's
  wireframes, flows and style guide, #183), `report/` (galip), `manual-checks/` (hasan,
  checklists a person reruns — root `AGENTS.md` §10), `literature/` (hasan, #10)
- ADRs are **not** here: they live in `memory-bank/decisions/`

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- Do not hand-edit generated files in `api/`.
- Deadlines: RS 23 Nov 2026, SDD 7 Dec 2026.
