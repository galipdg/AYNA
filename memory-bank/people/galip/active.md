# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-08 (main-checkout session: review round for the client stack). **This file lives on `galip/147-step-schema-rows` until #150 merges; `main` still has the 10-28 version.**
- Current issue: none in progress. Pushed 2026-11-08 on galip's OK:
  - `galip/147-step-schema-rows` (#150): `main` merged, ADR v0.2 Accepted with hasan's two corrections, and the three server tests that hard-coded `"version": "0.1"` now read `StepSchema.version()`. These are omer's files, so his review of that commit was requested on the PR. **galip merges #150 after that.**
  - `galip/71-request-log-race`: `_send` logs before writing (omer's 11-05 inbox fix). PR `Refs #71`, review requested from omer.
- Reviews given 2026-11-08 (all APPROVE): #154, #210, #192, #197. #154 is still BLOCKED by hasan's CHANGES_REQUESTED until he re-reviews; omer fixed his point in `a3d160b`. The client stack #186–#197 merges after #154.
- Inbox still to act on (not done today): omer #53 (three stale SDD references: `docs/rs/RS.md:285`, `ai/API.md:196`, `ai/ayna_ai/validate.py:29`; RS before #41); hasan #40/#35 (FR-35 has no "more than one element matched" category: hasan treats it as *element not found* with no healing; answer whether a sixth category is wanted); hasan #40 (`durationMs` in `docs/agent-rpc.md`); hasan #28/#7 (G0's last box: a 7–8B model returns valid JSON for a Turkish prompt; evidence is in PR #115, tick #28 with a link); hasan #201 (scorer uses unscaled coordinates; no v2 behaviour assumed in `heal/`).
- After #150 merges: `SelectRow` + row checks into RS FR-11/15/18; #37 prompt lines and the `column` enum when `columns` is non-empty; #36 grid labelling rules. Tell hasan on #40: the ADR still says a `column` against a list target is a playback error, while his 11-07 KeePass 2 measurement suggests `{value, column}` could work through the per-column `Text` children; #40 decides.
- Still open from 11-03 (see that version on this branch's history): #43 unblocked and not started; RS TBD-1/SC-07/NFR-02 after #169; `FEATURE_VERSION` → `heal/features.py` with #43; licence (TBD-7); iCloud Desktop checkout (fresh clone outside iCloud still advised).
- Local tools on this Mac: the client needs Node ≥ 22.12 → `/opt/homebrew/opt/node@22/bin` (the default `node` is 20.15). Server tests need Java 21 + Docker; the machine has Java 17 and Docker was not running, so they were not run here.
