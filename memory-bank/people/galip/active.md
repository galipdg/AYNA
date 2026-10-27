# Active — Galip Enes Doğan (`galip`)

Only galip's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-27 (orchestrator session: subagents opened PRs #137–#146)
- Current issue: none in progress locally. Everything not blocked by a teammate is in review.
- PRs in review (all CI green). The ones marked "stacked" must merge after their base:
  - #134 `Closes #13` step schema v0 → then #142 `Refs #37` generator (stacked on #134) → then #146 `Refs #71` NL service (stacked on #142); #145 `Refs #36` NL guideline + checker (stacked on #134)
  - #135 `Refs #16` agent RPC (waits on hasan's #12 for `snapshot`); #141 `Closes #49` healing scorer
  - #138 `Closes #19` workshop pre-read (**do not merge before the advisor agrees**: fill §7, tick criterion 2) · #137 `Closes #27` RS outline (needs all three approvals) · #140 `Closes #34` scenarios/FR/NFR · #143 `Closes #35` RS draft (stacked on #137, #140, #138; omer must review)
  - #144 `Closes #50` SDD AI sections in `docs/sdd/SDD-ai.md` (omer folds it into SDD.md at #53) · #139 `Refs #20` literature section 2 → into `omer/10-literature-review` (omer to add `Closes #20` to #126)
- Next step: get the advisor's answers to Q1–Q8 (`docs/requirements-workshop.md` §7 on PR #138), then propagate them into #140/#143. Run the #71 offline manual check (task note `tasks/71-nl-service.md`). Answer review comments.
- Blocked on teammates: #42 and #43 (hasan's #11/#12), the 40 pairs of #36 and then #57 (#33 ← #21 ← #6), #58 (omer's #25 + #36), #72 (#71 + #57), #76 (#49 + hasan's #46), #21 D1 (hasan's #6). #131 GPU request is on hold.
- Needs galip by hand (auto mode blocked GitHub issue writes):
  - comment on #21 and #80 that ADRs go to `memory-bank/decisions/`, not `docs/adr/`;
  - open issues for: step schema v0.2 (grid row select/check; #37/#36/#50 all hit it), the NFR-07/08 load test (TBD-9), and how healing proposals travel agent → server (#73/#74).
- Plan doc ("AYNA – 14-Week Project Plan (Merged)") fixes: "Decision models" row (only Decider is CPU), LLM gaps row ("not desktop" is wrong: UFO), RS lead Hasan → Galip, and the reference numbering clashes with `docs/literature.md` (TBD-11; asked omer).
- Inbox: handled but not yet deleted: omer #3, hasan #9, omer #7 (→ #131), omer #10. Delete them only when no open PR touches `people/galip/inbox.md` (#126 still does).
- Open questions: project licence (TBD-7, team decision before #41); 30 s service timeout is tight on a loaded laptop (#71); qwen3:8b matched gold on 3/12 trial pairs vs gemma4 9/12 (#36): input for #72/#80.
