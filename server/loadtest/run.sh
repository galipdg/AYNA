#!/usr/bin/env bash
# One command for the whole load test (#152): start a throwaway backend, seed it to the
# NFR-08 size, run the load test, then remove the backend and its data.
#
#   server/loadtest/run.sh                 # defaults: 10 clients, 20 s warm-up, 120 s measured
#   server/loadtest/run.sh --duration 300  # any load.py option is passed on
#   KEEP=1 server/loadtest/run.sh          # leave the backend running afterwards
#
# Needs Docker and Python 3.11+ (standard library only). Results go to server/loadtest/out/.
set -euo pipefail

cd "$(dirname "$0")"
export AYNA_LOADTEST_PORT="${AYNA_LOADTEST_PORT:-18090}"
url="http://127.0.0.1:${AYNA_LOADTEST_PORT}"
compose=(docker compose -f compose.yml)

teardown() {
	if [[ "${KEEP:-}" == "1" ]]; then
		echo "backend left running at ${url}; remove it with: docker compose -f $(pwd)/compose.yml down -v"
	else
		"${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
	fi
}
trap teardown EXIT

# A clean start every time, so the seed always lands in an empty database.
"${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
"${compose[@]}" up -d --build

mkdir -p out
python3 seed.py --url "$url" --out out/seed.json
python3 load.py --seed out/seed.json --out-dir out "$@"
