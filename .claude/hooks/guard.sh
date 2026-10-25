#!/bin/sh
# Starts guard.py with whatever Python 3 this machine has:
# macOS usually has only `python3`, Windows usually only `python`
# (the Windows Store `python3` stub fails the version check and is skipped).
# If no Python 3 is found, exit 0 so the session is never blocked by a missing interpreter.
here=$(dirname "$0")
for py in python3 python; do
  if "$py" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1; then
    exec "$py" "$here/guard.py"
  fi
done
echo "AYNA guard: no Python 3 found, hook skipped" >&2
exit 0
