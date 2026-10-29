# #49 Self-healing scorer v0

- Issue: https://github.com/galipdg/AYNA/issues/49
- Owner: galip · Branch: `galip/49-healing-scorer`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`agent/ayna_agent/heal/scorer.py` is a pure function over plain mappings, so it does not wait for hasan's descriptor (#11) and snapshot (#12). `score(target, candidate)` returns `ScoreResult(score, contributions, similarities)`; `rank(target, candidates, k=3)` returns `RankedCandidate(id, result)` sorted by score desc, id asc. S = Σ wᵢ·simᵢ / Σ wᵢ over the properties the target has. #42 (candidates) and #43 (graph features: `parentPath`, `siblingIndex`, `nearestLabel`, `windowTitle`) will feed it; #73 (playback, hasan) will call it; #74/#75 store and show the contributions.

The Similo → UIA mapping table, the sources and every similarity rule are in the module docstring (one place, next to the `SIMILO_WEIGHTS` constant). Tests: `agent/tests/test_heal_scorer.py`.

## Decisions (small, local to this task)
- 2026-10-27 — Mapping table in the module docstring, not `docs/healing-scorer.md`: `docs/` (outside rs/sdd/report) is hasan's, and the table belongs next to the weights constant. The SDD section (#45) can link it.
- 2026-10-27 — Weights are Similo's (1.5 for Tag, Id, Name, Visible text, Neighbor texts; 0.5 for the rest), taken from the paper §3.2 (arXiv:2208.00677v1) and the authors' code (github.com/michelnass/Similo2, `WidgetLocator.java`, `WEIGHTS` array). Area/shape normalisation (min/max) and the truncated-pixel location distance come from that code, because the paper does not state them.
- 2026-10-27 — `name` maps to Similo's *visible text* (Levenshtein), not its HTML `name` attribute, which is a developer identifier like `id` and is covered by `automationId`. HRef, Alt, IsButton are not mapped. `windowTitle` (from #43) has no Similo analogue and gets 0.5.
- 2026-10-27 (revised, orchestrator decision after the first PR version) — `automationId` compares only the leaf (text after the last `.`; ids without dots compare whole) with normalised Levenshtein. Qt's dotted AutomationId changes for every descendant when an ancestor is renamed (learnings 2026-10-25), and the ancestor chain is already scored by `parentPath`. The first version compared whole ids, which gave unrelated Qt siblings ~0.6 on that property because of the shared `QApplication.<window>.` prefix; now they get ~0.1–0.3 and an ancestor rename with the same leaf gets 1. #76 can still compare this with Similo's exact match.
- 2026-10-27 — `siblingIndex` uses equality (Similo's id-relative XPath analogue). An inserted control shifts indexes and gives the full 0.5 to the new occupant of the old index; location partly offsets it.
- 2026-10-27 (revised, orchestrator decision after the first PR version) — Missing-property rule: `None`, absent, blank strings and empty bounds are missing. If the *target* lacks a value, the property is skipped and its weight not counted (nothing to compare against). If only the *candidate* lacks it, similarity is 0 and the weight is counted, as in Similo (missing attribute = no match). Score 0 if the target has nothing to compare. The first version skipped on either side, which let a nameless candidate outrank the named correct one (`test_named_correct_candidate_beats_a_nameless_one` shows the case: 238/247 vs 379/494 under the old rule).
- 2026-10-27 — Exact arithmetic with `fractions.Fraction` (every similarity is rational; location uses `math.isqrt` like Similo's int truncation), so the contributions sum to the score exactly and ties are exact. No rounding policy needed; callers convert with `float()` at the JSON boundary.
- 2026-10-27 — Text normalisation: NFC, casefold, Turkish İ/I/ı folded to `i`, whitespace collapsed; other diacritics stay significant. Folding ı/i merges rare minimal pairs (`sıra`/`sira`), which is acceptable for a similarity score.
- 2026-10-27 — `bounds` = `(left, top, right, bottom)` (Win32 RECT order, as in the #6 dump), floats rounded to pixels. `weights=` replaces the whole table (unnamed properties get 0), so "AutomationId only" for RQ4 is `weights={"automationId": 1}`.
- 2026-10-27 — No new dependency: Levenshtein is ~15 lines of plain Python.
- 2026-10-29 — DPI (hasan's #141 review §3): of his two options, `dpi` read per element rather than a cut-off parameter. A per-element value also covers a target recorded at 100 % and candidates captured at 150 %, which one cut-off cannot. Each element's corners and area are converted to DIP (physical * 96 / dpi) only inside the comparison; missing `dpi` means 96, so existing inputs score exactly as before. The distance stays exact: `isqrt(floor(x)) == floor(sqrt(x))`.
- 2026-10-29 — hasan's note that `normalize_text` drops the dot from `ż` is not quite right: NFC makes `ż` one character, so it keeps the dot. Only a U+0307 that stays separate after NFC is dropped (what `İ` leaves after casefold, or a dot on a letter with no precomposed form). The docstring now says that.

## Status
- [x] Branch, task note, board → In progress
- [x] `heal/scorer.py` + 51 tests (ruff check, ruff format --check, pytest pass on macOS, Python 3.12)
- [x] 2026-10-27 revision on the same PR: target-only missing rule and leaf-only automationId; 55 tests pass
- [x] Inbox notes to hasan (descriptor alignment) and omer (HealingProposal shape)
- [x] PR https://github.com/galipdg/AYNA/pull/141 opened 2026-10-27; CI green (agent job on Windows included)
- [x] PR review: omer and hasan approved; #141 merged 2026-10-29
- [x] Follow-up from hasan's #141 review §3 (2026-10-29, branch `galip/49-dpi-location`): optional `dpi` per element; location and area compared in DIP (`LOCATION_CUTOFF_DIP`), shape unchanged; `parentPath` must use programmatic ControlType names; U+0307 note corrected. 129 agent tests pass (`-m "not windows"`)
- Next step: #42 / #43 feed real snapshot data; #43 puts `dpi` on every element (hasan).

## Manual checks
- None needed: pure Python, fully covered by unit tests. Speed (2026-10-27, M2, Python 3.12): 1,000 candidates ranked in ~0.4 s (~0.4 ms each).

## Open issues
- No minimum score: like Similo, `rank` always returns candidates. The threshold belongs to #73 (and #103 later).
- ~~Bounds are raw pixels~~ — done 2026-10-29: `dpi` per element, location and area in DIP. Bounds stay physical in every document (hasan: one coordinate space through the system).
- Neo4j cannot store a map as a property; per-candidate contributions probably belong on the `CANDIDATE` relationship, not the `HealingProposal` node (`docs/graph-model.md`). Raised with omer (#74).
- Key names are camelCase (graph model) while #11 lists snake_case Python fields; an adapter or a shared choice is needed. Raised with hasan.

## Handoff
- On this Mac, files under the worktree carry the macOS `hidden` flag, and recent Python (seen with 3.12.9) skips hidden `.pth` files, so `pip install -e` does not take effect: run `python -m pytest` from `agent/` (see learnings 2026-10-27).

## Outcome (fill when the issue closes)
