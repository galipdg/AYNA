# #152 Server load test for NFR-07 / NFR-08

- Issue: https://github.com/galipdg/AYNA/issues/152
- Owner: omer · Branch: `omer/152-load-test`
- Started: 2026-11-10 · Last update: 2026-11-10

## Approach
`server/loadtest/`: `seed.py` fills one application through the REST API, `load.py` runs 10
threads (one session and keep-alive connection each) through an editor session plus a run, and
`run.sh` does both against a throwaway backend (`compose.yml`, project `ayna-loadtest`). How to
read the numbers is in `server/loadtest/README.md`.

## Decisions (small, local to this task)
- 2026-11-10 — Tool: Python standard library (`http.client`, `threading`), omer's choice over k6 — no new dependency, runs on the closed network as is.
- 2026-11-10 — Seed through the REST API, not Cypher — the data passes the same validation as real data; 1 000 objects + 500 tests take ~25 s.
- 2026-11-10 — Own Compose project with no Neo4j host port — the load test never writes into a developer's running `ayna` backend (one was running here).
- 2026-11-10 — No think time by default (worst case); 20 s warm-up not counted; an error counts as late; percentiles by nearest rank.
- 2026-11-10 — Results live in `server/loadtest/results/` (omer's area), not `docs/` (hasan's); galip cites them from the RS.

- 2026-11-10 — From hasan's #225 review: `run.sh` probes `PYTHON`, `python3`, `python` by running them (Windows' `python3` is the Store stub); the outlier ceiling to watch is the client's 5 s request timeout; screenshot uploads (#51) to join the load behind `--screenshots` once #51 is on `main`.

## Status
- [x] seed, load test, one command (`server/loadtest/run.sh`)
- [x] first run recorded: `results/2026-11-10-apple-m3.md` — 105 443 requests, 100 % within 500 ms, p95 31.9 ms, 0 errors → NFR-07 met
- [ ] RS: NFR-07 / NFR-08 confirmed — galip's file; request in `people/galip/inbox.md`
- Next step: push and open the PR on omer's OK (`Closes #152` only once galip's RS change exists; until then "Part of #152").

## Manual checks
- none needed: every criterion is checked by running `run.sh` (done 2026-11-10 on omer's Mac).

## Open issues
- After #51 merges: add `--screenshots` to `load.py` (upload a ~200 KB PNG per step result, counted in the load but not in the NFR-07 share) and run again; hasan will run it on Windows both ways.
- SDD test-design row (`docs/sdd/SDD.md` ≈ line 823, "Planned per NFR") should say the load test is built; left for after #222 merges, which edits the same file.
- Not measured: WebSocket live updates (NFR-06) and login; a run on the Windows demo machine would be a stronger number than a Mac running both sides.

## Handoff
The load generator shares the CPU with the backend; Docker Desktop had 4 CPUs / 4.1 GiB. A short
run with only 3 s warm-up was about twice as slow (p95 57 ms), so keep the warm-up.

## Outcome (fill when the issue closes)
