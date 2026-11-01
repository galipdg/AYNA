# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01
- Current issue: **#161** — PR #170. Galip's review (changes requested, 2026-10-31) is
  addressed on `hasan/161-winforms-walk`; waiting on his re-review. **#169 must merge first,
  this branch is stacked on it.**
- Merged today: **#175** (#11 element descriptor v0, three approvals) and **#172** (the #17
  Windows check note into omer's inbox). #11 is closed, so `schemas/element.schema.json` and
  `agent/ayna_agent/model.py` are on `main`.
- Next step: push `hasan/161-winforms-walk`, answer galip's review on #170 point by point
  (what changed, what the re-measurement moved), and ask him to re-review. Then **#12**
  (snapshot export): it emits #11's descriptors under the budget #161 just measured —
  default property set = 17 plain properties + `LabeledBy`, no pattern probes, 5 000 ms per
  window as a deadline **on a timer**, `SnapshotTimeout` (-32002) with no partial document.
- Open on my side: **#169** (D1 pilot-apps ADR) has only a comment from galip, no approval
  yet; it blocks #170.
- Review queue: **empty**. #173 and #176 approved on 2026-11-01 (#174 merged before I got to
  it — still worth checking on `main` that `scoredElement` accepts `dpi` and stays a subset of
  the element descriptor, which was my #11 open issue). Both reviews carry one thing galip
  must decide: on #173, whether a model server that is **not running** should keep arriving as
  a 504 `timeout` on Windows (it does, because a closed loopback port times out here instead
  of being refused) — he may open an issue or ask me to. The one-liners I asked for in this
  PR: on #173 refuse or support an IPv6 listen address (`--host ::1` passes the loopback
  check and then dies at bind, `ThreadingHTTPServer` being AF_INET); on #176 an explicit
  LF newline in the test that writes `heldout.jsonl`, which is red on Windows and will be
  red in #122's Windows job once the dataset tests move there. See `learnings.md`
  2026-11-01 for the connect-timeout trap: the same one is in the agent RPC handshake
  (#16/#135) and the client's process manager (#17).
- Watch out: a **`copilot-swe-agent[bot]`** merge commit was pushed to
  `hasan/161-winforms-walk` on 2026-11-01 (`d261faa`, "resolve conflicts with main",
  co-authored by omer). It kept both ADR index lines but **left a literal `<<<<<<< HEAD`
  marker** in `memory-bank/decisions/README.md`, which I removed in this branch. Check that
  file whenever that bot touches a branch of mine, and ask omer what the bot is for.
- Open questions:
  - Criterion 2 of #21 (pilot apps "installed on every member's machine" cannot hold for two
    macOS members) — needs the team; wording is in `tasks/21-pilot-apps-decision.md`.
  - The #21 issue names `docs/adr/ADR-001-pilot-apps.md`; the ADR went to
    `memory-bank/decisions/` per the memory-structure ADR. The issue text should be corrected.
  - Galip owes a decision on the one-sided `dpi` fallback in the healing scorer (my #166
    review); omer needs `dpi` in the graph model before #25 persists elements.
- Small follow-up branch waiting (not started): the pre-ADR ownership tables in
  `docs/working-agreement.md` §1 and `docs/README.md` (galip's #19 note), and the
  `requirements.txt` mentions in `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- Inbox: everything up to 2026-10-29 is handled, plus omer's #122 note (PR #167 merged).
  Do not delete the handled lines yet — PRs #157, #150 and #126 still add lines to that file
  and `merge=union` would bring deleted ones back. Trim once those have merged.
- Waiting on: galip's re-review of #170 and his approval on #169; galip + omer on the D1 ADR.
