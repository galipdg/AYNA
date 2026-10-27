# Inbox — Ömerfaruk Sarıbal (`omer`)

Anyone may append; only omer removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from galip · ADR windows-work-to-hasan · You took over #18 (tool comparison matrix) and #48 (SDD test-design section) from hasan, and now own `docs/sdd/` (each component owner still writes their own section). Your Windows-checked client issues (#24, #44, #75, #100) and the installer/air-gapped tests (#84, #85, #91, #108) stay with you.
- 2026-10-27 · from galip · #13 · Step schema v0 is ready for your review on `galip/13-step-schema` (PR to follow; needs all three approvals): ADR `2026-10-27-step-schema-v0`. For the server and editor: the API shape is `{version: "0.1", steps: [...]}`; step `id` is optional (the server assigns a UUID on save); `timeoutMs` is camelCase. Neo4j cannot store maps, so `Step.checkpoint` needs flattening or a JSON string, and `Step` needs `timeoutMs` — `docs/graph-model.md` lists only keyword, value, checkpoint. Client-side validation can use the same file with ajv's 2020-12 build; `schemas/examples/step/cases.json` has named valid/invalid cases to reuse in your tests.
