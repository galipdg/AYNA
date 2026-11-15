#!/usr/bin/env bash
# Breaking-change check for the REST contract (#52, ADR contracts-v1-freeze).
#
# Compares docs/api/openapi.yaml with its version at a base git ref using oasdiff and fails on
# anything oasdiff rates ERR or WARN. The generated document marks no response property as
# required, and oasdiff rates removing an optional response property only INFO, so
# oasdiff-levels.txt raises that check to ERR: a client may read the property.
# A breaking change passes only together with a new major `info.version` (OpenApiConfig.java).
#
# Usage: .github/contracts/rest_compat.sh <base git ref> [oasdiff binary]
set -euo pipefail

base_ref="$1"
oasdiff="${2:-oasdiff}"
spec=docs/api/openapi.yaml
levels="$(dirname "$0")/oasdiff-levels.txt"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if ! git cat-file -e "$base_ref:$spec" 2>/dev/null; then
  echo "rest: $spec is new at $base_ref, nothing to compare"
  exit 0
fi
git show "$base_ref:$spec" > "$work/base.yaml"

# The `version:` line directly under `info:` (the generated file always has this shape).
info_version() {
  awk '/^info:/ { info = 1; next } /^[^ ]/ { info = 0 } info && /^  version:/ { print $2; exit }' "$1" | tr -d '"'
}
major() {
  local v="${1#v}"
  echo "${v%%.*}"
}

old_version="$(info_version "$work/base.yaml")"
new_version="$(info_version "$spec")"
echo "rest: $base_ref has $old_version, this tree has $new_version"

if [ "$(major "$new_version")" -gt "$(major "$old_version")" ] 2>/dev/null; then
  echo "rest: major version $old_version -> $new_version, breaking changes are listed but allowed"
  "$oasdiff" breaking "$work/base.yaml" "$spec" --severity-levels "$levels"
  exit 0
fi

if ! "$oasdiff" breaking "$work/base.yaml" "$spec" --severity-levels "$levels" --fail-on WARN \
  --format githubactions; then
  echo "::error file=$spec::Breaking REST change at version $new_version. Keep the old shape (add, do not change or remove), or write an ADR and raise the major version in OpenApiConfig.java."
  exit 1
fi
echo "rest: no breaking change against $base_ref"
