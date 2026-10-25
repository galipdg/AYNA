"""PreToolUse guard for AYNA (Claude Code).

Blocks (exit 2):
  * git push to main/master, force pushes, deleting main/master
  * edits to another person's private memory (people/<other>/active.md, journal.md)
Fails open (exit 0) on any unexpected error so it never breaks a session.
"""
import json
import os
import re
import sys

PEOPLE = {"galip", "omer", "hasan"}


def block(reason: str) -> None:
    print(f"Blocked by AYNA guard: {reason} (see AGENTS.md)", file=sys.stderr)
    sys.exit(2)


def current_user(project_dir: str):
    path = os.path.join(project_dir, "CLAUDE.local.md")
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"ayna-user:\s*(\w+)", f.read())
            return m.group(1).lower() if m else None
    except OSError:
        return None


def check_bash(cmd: str) -> None:
    for part in re.split(r"&&|\|\||;|\n", cmd):
        p = part.strip()
        if not re.match(r"^git\s+push\b", p):
            continue
        if re.search(r"(\s|^)(-f|--force|--force-with-lease)(\s|=|$)", p) or re.search(r"\s\+\S", p):
            block("force push is not allowed")
        if re.search(r"(\s|:)(main|master)(\s|$)", p) or re.search(r"--delete\s+(main|master)\b", p):
            block("pushing to or deleting main is not allowed; push your own branch and open a PR")


def check_edit(path: str, project_dir: str) -> None:
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(project_dir)).replace("\\", "/")
    m = re.match(r"memory-bank/people/([^/]+)/(active|journal)\.md$", rel)
    if not m:
        return
    owner = m.group(1)
    me = current_user(project_dir)
    if me is None:
        block("set 'ayna-user: <id>' in CLAUDE.local.md before editing people/ memory")
    if owner != me:
        block(f"people/{owner}/{m.group(2)}.md belongs to {owner}; write to people/{owner}/inbox.md instead")


def main() -> None:
    try:
        data = json.load(sys.stdin)
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
        tool = data.get("tool_name", "")
        tin = data.get("tool_input", {}) or {}
        if tool == "Bash":
            check_bash(tin.get("command", ""))
        elif tool in ("Edit", "Write", "MultiEdit"):
            check_edit(tin.get("file_path", ""), project_dir)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
