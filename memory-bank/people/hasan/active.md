# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01 (second session of the day)
- Current issue: **#12** (window snapshot export) — **done and pushed as PR #180**, `Closes #12`,
  CI **5/5 green**, no conflict. Waiting on galip's and omer's review; the ADR
  `2026-11-01-snapshot-schema-v0` is **Proposed** and needs all three of us.
- All three acceptance criteria met, the first one **measured**: the trial app's login window is
  14 elements in **28–32 ms** over six runs against the 2 s bound.
- **#16 is answered too**: `snapshot` works end-to-end through galip's RPC server. I commented on
  #16 asking him to close it or say what else it needs.
- Merged into `main` today while I worked: #178 (my review notes), #157, #155, #160. I merged
  `origin/main` into my branch and resolved one conflict in the ADR index (origin was right: the
  graph-schema ADR is now Accepted and the REST problem-details ADR is new).

## What #12 delivered

Two commits plus a portability fix, deliberately in that order:

1. **The contract first** — omer had asked on #12 twice and #15, #24, #25 and the G0 demo (#28,
   9 Nov) were blocked on the *shape*, not the code. `schemas/snapshot.schema.json` 0.1, a real
   example (`examples/snapshot/trial-login.json`, the trial app's 14 elements, rebuilt by the
   tests so it cannot drift), 39 named cases, the ADR, the `snapshot` success example in
   `docs/agent-rpc.md`, and `schemas/README.md` sections for the snapshot **and** the element
   descriptor (#11 never added one).
2. **The backend** — `recognition/snapshot.py` (document, canonical text, round trip) and
   `recognition/uia.py` (`UiaDesktop`: `setup`/`close`, `list_windows`, `snapshot`), wired into
   `rpc.main()`. 95 new tests; whole agent suite 280, macOS selection 276 + 4 deselected.

Shape decisions, in case they are challenged in review: `elements` is a **flat array in pre-order**
of `{id, parentId, element}`, one root per snapshot, ids `e<position>` and opaque; the descriptor is
**duplicated** from `element.schema.json` (a `urn:` `$ref` needs a registry in three languages) with
a test comparing both property maps including constraints; an incomplete walk is **-32002 with no
document at all**, no `truncated` flag and no depth or element limit that yields a partial tree.

## Measured today, worth not re-deriving

- Trial app login window: **14 elements, 28–32 ms** (2.04 ms per element), DPI 120.
- KeePass 2 in the #161 state: main window **114 elements in 819 ms**, `Add Entry` 40 in 363 ms.
  74 + 40 = 114, so the dedup is confirmed on a real owned dialog. Against #161's 2.26 s for the
  same window: the difference is the **reader**, not the framework — the snapshot reads only the 12
  properties the descriptor stores and no pattern probes. So the 5 000 ms budget has far more room
  than #161 could claim.
- **The timer design is necessary and it works.** A Qt window whose GUI thread slept 40 s: the
  *first* UIA read blocked, so no between-element clock check could ever have fired. `-32002` came
  back after **2 251 ms** of a 2 000 ms budget, twice in the same process, and the window
  snapshotted normally again (58 ms) after it thawed. One daemon thread leaks per timeout, counted
  in `UiaDesktop._abandoned` and logged by `close()`.

## Three things I changed that are not mine, all in the owners' inboxes

- `rpc.main()` builds `UiaDesktop()` — the one-line swap galip offered on #16.
- **A real bug in `rpc.py`:** `python -m ayna_agent.rpc` imports the module as `__main__`, so the
  backend's `from ayna_agent.rpc import UiaUnavailable` loaded it a *second* time and the two
  copies had two different exception classes — a backend error came out as `-32603` instead of
  `-32001`. The `__main__` block now delegates to `ayna_agent.rpc.main`. Only the subprocess CLI
  test could see it.
- `test_cli_announces_its_port_and_answers` asserted `-32001` from the placeholder backend; it now
  accepts either the window list or `-32001`.

**One departure galip may reject:** `UiaDesktop.setup()` records why UIA is unavailable instead of
raising, against his "a failing `setup()` stops the server". `docs/agent-rpc.md` says a host
without a backend answers `-32001` per call, and a hard failure would stop galip and omer from
running the client, the Spy or that very test on macOS. Three lines to change back, plus a fallback
to `UnavailableDesktop` in `main()`.

## Next step

Nothing of mine is unpushed and no issue is in progress. In order:

1. **Answer the #180 review** when it arrives; flip the ADR to Accepted once all three approve.
2. **#169** (D1 pilot-apps ADR) still has no approval and it **blocks #170** (#161). That is the
   oldest thing stuck on my side — chase galip and omer for it.
3. Then propose the next issue from the milestone (`gh issue list --assignee @me --state open`).
   #22 (Spy backend) and #23 (win32 fallback) now have a working `recognition/` to build on.

## Open issues I raised and did not fix

- **`minLength: 1` cannot say "not only spaces".** Both `snapshot.schema.json` and
  `element.schema.json` promise a whitespace-only string is never stored and only enforce
  non-empty. The agent honours it (`model._blank`); a Java or TypeScript producer could write
  `"   "` and be valid. Named as a *valid* case in `examples/snapshot/cases.json` and raised under
  "Open, for the deciders" in the ADR. My recommendation: `"pattern": "\\S"` on every string
  property in **both** schemas, one PR bumping both to 0.2, **after** #15 and #24 land against 0.1.
- The element-descriptor ADR still says `Proposed (#11)` although #11 closed with three approvals
  (PR #175). Someone must flip it; I asked galip.
- `schemas/AGENTS.md` names only the step schema's tests, in `ai/`. The element and snapshot
  schemas are tested in `agent/`. It needs a line, but it is an `AGENTS.md`, so **ask the user**.
- **Only Python 3.13 exists on this machine**, while every module declares `>=3.11`. Two tests
  passed locally and failed in CI because `Path.read_text(newline=...)` is 3.13-only. A green local
  run is **not** evidence that the version floor holds — see `learnings.md` 2026-11-01.
- `schemas/README.md` and the ADR refer to `eval/spikes/uia-walk-cost.md`, which is still on
  `hasan/161-winforms-walk` (PR #170). Written as a forward reference, not a link, so nothing is
  dead on `main`; make it a link once #170 merges.
- Unverified: a **second monitor at another scaling**. Every number above is from one 120-DPI
  display, so `dpi` has only ever been 120 and no snapshot has had negative `bounds`. One check at
  the weekly Windows session.

## Still open from earlier, unchanged

- Criterion 2 of #21 (pilot apps "installed on every member's machine" cannot hold for two macOS
  members) — needs the team; wording is in `tasks/21-pilot-apps-decision.md`. And the #21 issue
  names `docs/adr/ADR-001-pilot-apps.md` while the ADR went to `memory-bank/decisions/`.
- Galip owes a decision on the one-sided `dpi` fallback in the healing scorer (my #166 review);
  omer needs `dpi` in the graph model before #25 persists elements.
- Galip to decide, from my #173 review: whether a model server that is **not running** should keep
  arriving as a 504 `timeout` on Windows (a closed loopback port times out here instead of being
  refused). Plus the two one-liners: #173's IPv6 listen address, #176's explicit LF newline.
- Small follow-up branch, not started: the pre-ADR ownership tables in `docs/working-agreement.md`
  §1 and `docs/README.md` (galip's #19 note), and the `requirements.txt` mentions in
  `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- A `copilot-swe-agent[bot]` left a literal `<<<<<<< HEAD` in `memory-bank/decisions/README.md`
  and it reached `main`. Fixed on both sides by now, but **check that file whenever that bot
  touches a branch of mine**, and ask omer what the bot is for.
- Review queue: **empty**.
- Inbox: handled up to 2026-10-31. Do not delete the handled lines yet — PRs #150 and #126 still
  add lines to that file and `merge=union` would bring deleted ones back.
