# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29 (review round: approved #160, #159, #155, #157; flipped the step schema v0 ADR to Accepted on #150; RS review follow-ups in PR #164)
- Current issue: none in progress. Open PRs of mine: **#164** (`Refs #35`, RS 0.6 with the #143 review comments; reviews requested from omer and hasan; after merge tick #35 criterion 2) and **#150** (`Refs #147`, step schema v0.2 rows). omer approved; hasan holds it until he re-reads `2e50749` (cell text rule is non-empty-Value-first, not his Name-first; reasons in the PR comment of 2026-10-29). After it merges: `SelectRow` into RS FR-11, `column` limited to known headers in the #37 derivation, adopt in the #36 guideline.
- Merged 2026-10-29: #134, #135, #137, #139–#146, #151. #138 was closed (empty after #143 carried its files); #19 stays open until §7 of `docs/requirements-workshop.md` is filled.
- Decided 2026-10-29 (galip): **retrieval — the server picks the candidate objects**; the AI service has no Bolt edge. Server gets the instruction's vector from `POST /ai/embed`, runs current-screen + vector top-k queries, sends `objects` to `/ai/generate-steps`. To do: update #58's expected output (was `ai/ayna_ai/retrieve.py`), SDD-ai AI-4 / AI-9 #5, `ai/API.md` "Until retrieval exists" (says the service will choose candidates itself). Asked omer on #155 whether galip writes the Cypher in `server/` under his review.
- Review follow-ups asked of galip on merged PRs (none blocks anyone today; most are "before the #52 freeze"):
  - **RS `docs/rs/RS.md`**: omer's and hasan's #143 lists are done in PR #164 (FR-30, FR-23 exit codes 0/1/2, TBD-5/6/9/10 closed, FR-35 "search incomplete", NFR-45/46). Left: REST API row → v0 once #160 merges (omer #31 inbox); `SelectRow` + row checks into FR-11/15/18 after #150.
  - **`ai/API.md` / service** (#146, #142): `app` = application id (UUID), `version` = version id, `screen` = logical-name prefix (omer); `--allow-remote` should require a token (`AYNA_AI_TOKEN`, hasan); reasons opt-in per request (hasan, suggestion); loopback guard trusts `localhost` name resolution (hasan).
  - **SDD-ai** (#144): AI-5.2 "under 1 s per object, measured from an available snapshot; capture is NFR-02 / #12".
  - **heal scorer** (#141): `LOCATION_CUTOFF_PX = 100` is physical pixels, so it disagrees across DPI (hasan: please fix); write the input-contract constraint he asked for.
  - **#151 ADR / v0.2 doc**: `featureVersion` (or extractor id + version) next to proposals; say explicitly that an `aborted` run makes the gap visible; screenshot crop note; one line that notifications carry no `id`.
  - **NL dataset** (#145): quoting required for team-written pairs; style enum; `settings` pairs.
  - **#19 §7** after the advisor meeting, with UC-14 exit codes 0/1/2 (#149 ADR), Q5 scoped to the sample app (#161), Q7/CON-02 naming the pilots (KeePass 2 + HandBrake, #159).
  - hasan asked to tick the "ADR added" DoD box in the bodies of #141, #142, #145, #146 (reason is already inline). Auto mode blocks PR-body edits; galip runs it by hand.
- Blocked on teammates: #42 and #43 (hasan's #11/#12), the 40 pairs of #36 and then #57 (#33 ← #21 ← #6), #58 (omer's #25 + #36), #72 (#71 + #57), #76 (#49 + hasan's #46), #21 D1 (hasan's #6, now in PR #159). #131 GPU request is on hold.
- Inbox: handled but not yet deleted: omer #3, hasan #9, omer #7 (→ #131), hasan #16 (step schema v0 flip, done on #150). Delete them only when no open PR touches `people/galip/inbox.md` (#126, #155, #157, #159, #160 still do; GitHub ignores `merge=union`).
- Open questions: project licence (TBD-7, team decision before #41); plan-doc copy and reference numbering (TBD-11, waits on #126); 30 s service timeout on a loaded laptop (#71, measured on Windows in hasan's #162); qwen3:8b 3/12 vs gemma4 9/12 on the trial pairs (#36): input for #72/#80.
