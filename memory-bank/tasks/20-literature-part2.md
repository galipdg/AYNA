# #20 Literature review part 2 (LLMs in GUI testing, decision models)

- Issue: https://github.com/galipdg/AYNA/issues/20
- Owner: galip · Branch: `galip/20-literature-part2` (from `omer/10-literature-review`, PR into that branch)
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
Section 2 of `docs/literature.md`, in the entry format of section 1 (citation · finding · what it means for AYNA · source checked). Three themes: LLMs for GUI testing; grounding and output control; decision models and calibration. Ends with the "authoring time only" paragraph (acceptance criterion 2). The file lives on omer's #10 branch (draft PR #126), so this branch starts there and its PR targets that branch, as galip's #10 entries did (PR #132).

## Decisions (small, local to this task)
- 2026-10-27 — 11 sources: survey [14], GPTDroid [15], AUITestAgent [16], UFO, RAG, Willard & Louf, llama.cpp grammar docs, Guo, Jev, Strands Decider, H2O-Lightning-4B. Willard & Louf is added because the plan cites only llama.cpp for constrained decoding, and a docs page does not explain the mechanism.
- 2026-10-27 — Numbering: `literature.md` numbers ([3] Hammoudi … [14]–[16], [23] Healenium, [31]–[33]) do not match the current plan export ("AYNA – 14-Week Project Plan", References: [9] Hammoudi, [20] Healenium, [21] survey, [22] GPTDroid, [23] AUITestAgent, [24] UFO, [25] Jev, [26] Decider, [27] H2O, [31] RAG, [33] llama.cpp, [35] Guo). Kept [14]–[16] so the gaps table stays valid; new sources get provisional numbers [40]–[47], above every number used by the file ([3]–[33]) or the plan export ([1]–[39]). Mapping to the plan export: [40] UFO = plan [24], [41] RAG = [31], [42] Willard & Louf = not in plan, [43] llama.cpp grammars = [33], [44] Guo = [35], [45] Jev = [25], [46] Decider = [26], [47] H2O = [27]. Asked omer which plan version the file follows (his inbox, 2026-10-27).
- 2026-10-27 — Gaps table LLM row changed: the old gap said "not desktop", but UFO [40] is a Windows desktop agent on pywinauto/UIA. New row adds UFO and names run-time decisions (not repeatable) as the gap. The current plan export already has a similar row ("UFO lets an LLM decide every action on Windows"), so the plan needs only a wording check.
- 2026-10-27 — PDFs that WebFetch could not read (GPTDroid, survey) were saved by WebFetch and converted to text locally with a JXA/PDFKit script in the session scratchpad (no new dependency; the Swift toolchain on this Mac is broken).

## Status
- [x] Branch, task note, board In progress
- [x] All 11 sources read (see "Source checked" per entry)
- [x] Section 2 written, gaps table LLM row updated
- [ ] PR into `omer/10-literature-review`, review by omer
- Next step: after omer merges the PR into his branch, ask him to add `Closes #20` to PR #126; then update the plan's references and gaps table (galip, Claude Docs) once the numbering question is answered.

## Manual checks
- none (documentation only)

## Open issues
- Plan "Decision models" row says the 2026 models "run on CPU". Only Strands Decider's README says so; H2O-Lightning-4B's card measures GPUs only (a GGUF build exists, CPU speed unpublished); Jev is a hosted API in early access, so it cannot be used on a closed network at all. Fix the row in the plan (galip) and measure CPU latency in D7 (#103).
- H2O-Lightning-4B floors yes/no answers at 0.801 by default (`SHIM_NOUL_FLOOR=0` turns it off). Any threshold experiment in #103 must turn the floor off, or the probabilities between 0.2 and 0.8 never appear.
- Plan reference [27] (HPCwire / BigDATAwire) returns 403; the same Business Wire release was read on FinancialContent. Consider citing the model card instead.
- Not read: Strands Decider `evaluation/results.md`, the JevBench repository/leaderboard, TypeSafe's evals site and FAQ answers, the NAACL camera-ready of UFO (arXiv v5 was read), Willard & Louf's timing figure (not in the HTML text).
- AUITestAgent is a preprint whose text contradicts its tables in places; numbers in the entry follow the tables.

## Handoff
- Every number in section 2 comes from what was read on 2026-10-27; the vendor sources (Jev, Decider, H2O) are self-reported and say so.
- The RS (galip) should cite from this file once the numbering is settled; the mapping above converts to the plan export.

## Outcome (fill when the issue closes)
