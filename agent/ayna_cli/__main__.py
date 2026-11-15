"""`python -m ayna_cli` — the same entry point the `ayna` script uses."""

from ayna_cli.cli import console_entry

if __name__ == "__main__":
    raise SystemExit(console_entry())
