# #49 Self-healing scorer v0

- Issue: https://github.com/galipdg/AYNA/issues/49
- Owner: galip · Branch: `galip/49-healing-scorer`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`agent/ayna_agent/heal/scorer.py` is a pure function over plain mappings, so it does not wait for hasan's descriptor (#11) and snapshot (#12). `score(target, candidate)` returns `ScoreResult(score, contributions, similarities)`; `rank(target, candidates, k=3)` returns `RankedCandidate(id, result)` sorted by score desc, id asc. S = Σ wᵢ·simᵢ / Σ wᵢ over the properties compared for the pair. #42 (candidates) and #43 (graph features: `parentPath`, `siblingIndex`, `nearestLabel`, `windowTitle`) will feed it; #73 (playback, hasan) will call it; #74/#75 store and show the contributions.

The Similo → UIA mapping table, the sources and every similarity rule are in the module docstring (one place, next to the `SIMILO_WEIGHTS` constant). Tests: `agent/tests/test_heal_scorer.py`.

## Decisions (small, local to this task)
- 2026-10-27 — Mapping table in the module docstring, not `docs/healing-scorer.md`: `docs/` (outside rs/sdd/report) is hasan's, and the table belongs next to the weights constant. The SDD section (#45) can link it.
- 2026-10-27 — Weights are Similo's (1.5 for Tag, Id, Name, Visible text, Neighbor texts; 0.5 for the rest), taken from the paper §3.2 (arXiv:2208.00677v1) and the authors' code (github.com/michelnass/Similo2, `WidgetLocator.java`, `WEIGHTS` array). Area/shape normalisation (min/max) and the truncated-pixel location distance come from that code, because the paper does not state them.
- 2026-10-27 — `name` maps to Similo's *visible text* (Levenshtein), not its HTML `name` attribute, which is a developer identifier like `id` and is covered by `automationId`. HRef, Alt, IsButton are not mapped. `windowTitle` (from #43) has no Similo analogue and gets 0.5.
- 2026-10-27 — `automationId` uses normalised Levenshtein instead of Similo's exact match, because Qt's dotted AutomationId changes for every descendant when an ancestor is renamed (learnings 2026-10-25). Cost: unrelated Qt elements share the `QApplication.<window>.` prefix and get ~0.6 on that property. #76 should compare both.
- 2026-10-27 — `siblingIndex` uses equality (Similo's id-relative XPath analogue). An inserted control shifts indexes and gives the full 0.5 to the new occupant of the old index; location partly offsets it.
- 2026-10-27 — Missing-property rule (as specified by the orchestrator): compared only when both sides have a value; `None`, absent, blank strings and empty bounds are missing; skipped weights are not counted. Score 0 if nothing is comparable.
- 2026-10-27 — Exact arithmetic with `fractions.Fraction` (every similarity is rational; location uses `math.isqrt` like Similo's int truncation), so the contributions sum to the score exactly and ties are exact. No rounding policy needed; callers convert with `float()` at the JSON boundary.
- 2026-10-27 — Text normalisation: NFC, casefold, Turkish İ/I/ı folded to `i`, whitespace collapsed; other diacritics stay significant. Folding ı/i merges rare minimal pairs (`sıra`/`sira`), which is acceptable for a similarity score.
- 2026-10-27 — `bounds` = `(left, top, right, bottom)` (Win32 RECT order, as in the #6 dump), floats rounded to pixels. `weights=` replaces the whole table (unnamed properties get 0), so "AutomationId only" for RQ4 is `weights={"automationId": 1}`.
- 2026-10-27 — No new dependency: Levenshtein is ~15 lines of plain Python.

## Status
- [x] Branch, task note, board → In progress
- [x] `heal/scorer.py` + 51 tests (ruff check, ruff format --check, pytest pass on macOS, Python 3.12)
- [x] Inbox notes to hasan (descriptor alignment) and omer (HealingProposal shape)
- [ ] PR review (HasanBerk18, omerfaruksaribal), CI on Windows
- Next step: address review comments on the PR; then #42 / #43 feed real snapshot data.

## Manual checks
- None needed: pure Python, fully covered by unit tests. Speed (2026-10-27, M2, Python 3.12): 1,000 candidates ranked in ~0.4 s (~0.4 ms each).

## Open issues
- **Missing values are not penalised** (rule above): a nameless or unlabelled candidate can outrank a named one whose name differs (`test_missing_candidate_value_is_not_penalised`). Alternative to measure in #76: skip only when the *target* lacks the value; a candidate lacking it gets similarity 0.
- No minimum score: like Similo, `rank` always returns candidates. The threshold belongs to #73 (and #103 later).
- Bounds are raw pixels; the literature note asks for DPI normalisation. Both snapshots of a pair usually come from the same machine; revisit if #42's controlled versions mix scales.
- Neo4j cannot store a map as a property; per-candidate contributions probably belong on the `CANDIDATE` relationship, not the `HealingProposal` node (`docs/graph-model.md`). Raised with omer (#74).
- Key names are camelCase (graph model) while #11 lists snake_case Python fields; an adapter or a shared choice is needed. Raised with hasan.

## Handoff
- On this Mac, files under the worktree carry the macOS `hidden` flag, and recent Python (seen with 3.12.9) skips hidden `.pth` files, so `pip install -e` does not take effect: run `python -m pytest` from `agent/` (see learnings 2026-10-27).

## Outcome (fill when the issue closes)
