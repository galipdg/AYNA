# Server load test (#152)

Checks NFR-07 (95 % of REST requests within 500 ms) under the load of NFR-08 (10 clients at the
same time, 1 000 repository objects and 500 tests in one application). Python standard library
only, so it runs on the closed network with nothing to install but Docker and Python 3.11+.

## Run it

From the repository root:

```bash
server/loadtest/run.sh
```

This builds the server from the working tree, starts a throwaway backend (`compose.yml`: project
`ayna-loadtest`, its own Neo4j volume, server on `127.0.0.1:18090`, no Neo4j port on the host),
seeds it, runs the load test and removes the backend with its data. It never touches a backend
started with the root `docker-compose.yml`. Results go to `server/loadtest/out/` (git-ignored):
`load-<time>.md` and `.json`. Copy a run worth keeping to `results/`.

Options of `load.py` pass through: `run.sh --duration 300 --think-ms 1000`, `--clients 20`.
`KEEP=1 run.sh` leaves the backend up; `AYNA_LOADTEST_PORT` moves it off 18090.

Against a backend that is already running (it adds a new application named `Load test <time>`):

```bash
cd server/loadtest
python3 seed.py --url http://localhost:8080 --username admin --password '…'
python3 load.py --username admin --password '…'
```

## What it does

- `seed.py`, through the public API: 1 application and version, 10 imported window snapshots of
  100 controls each, 1 000 repository objects (one per control; primary `automationId`, backup
  `name` + `controlType`), 500 tests of 10 steps (Click, Type, Wait, Verify) over those objects.
- `load.py`: 10 threads, each logged in with its own session and keep-alive connection, repeat an
  editor session: list repository objects and tests, open 2 tests and 3 objects, save one of its
  own tests' steps, then run that test as the client does (create run, 10 step results, finish,
  read the run, list the test's runs). 22 requests per session.
- No pause between requests by default: ten people working at once never press this fast, so
  this is the worst case. `--think-ms` adds pauses.
- The first 20 s are run but not counted (JIT warm-up); then 120 s are measured.
- Per endpoint: count, errors, p50 / p95 / p99 (nearest rank) and max. Overall: the share of
  requests answered with 2xx within 500 ms; NFR-07 is met at ≥ 95 %. An error counts as late.

Not covered: snapshot imports, screenshot uploads and report downloads (NFR-07 excludes them;
the seed imports snapshots but they are not timed), WebSocket live updates (NFR-06), login.

## Reading the numbers

- The load generator runs on the same machine as the backend, so they share the CPU; on a
  dedicated server the numbers can only improve.
- The backend gets what Docker Desktop has (the result file records it): server and Neo4j together.
- Runs pile up during the test (about 4 500 in 120 s, 9 per test), so later requests see more
  history than a fresh database has.

## Results

| Date | Machine | Load | Requests | Within 500 ms | p95 | NFR-07 | File |
|---|---|---|---:|---:|---:|---|---|
| 2026-11-10 | Apple M3 MacBook, Docker 4 CPUs / 4.1 GiB | 10 clients, no think time, 120 s | 105 443 | 100.0 % | 31.9 ms | met | [results/2026-11-10-apple-m3.md](results/2026-11-10-apple-m3.md) |

The slowest endpoint is the repository list (`GET /api/apps/{appId}/repo-objects`, all 1 000
objects in one answer): p95 91 ms. The single slowest request (a step save, 1.8 s) is one of
105 443; it was not investigated (a garbage-collection pause is the usual cause) and does not change the verdict.
