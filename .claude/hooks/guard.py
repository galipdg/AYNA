"""PreToolUse guard for AYNA (Claude Code).

Blocks (exit 2):
  * git push to main/master (explicit refspec, HEAD while on main, or a bare push while on main),
    force pushes, --all/--mirror, deleting main/master; understands `git -C <dir>` and `-c k=v`
  * edits to another person's private memory (people/<other>/active.md, journal.md)
Fails open (exit 0) on any unexpected error so it never breaks a session.
"""
import json
import os
import re
import shlex
import subprocess
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


PROTECTED = {"main", "master"}
# git global options that take a separate value
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
# git push options that take a separate value
PUSH_OPTS_WITH_VALUE = {"--repo", "-o", "--push-option", "--receive-pack", "--exec", "--signed"}


def split_tokens(segment: str):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def current_branch(directory: str):
    try:
        out = subprocess.run(["git", "-C", directory, "rev-parse", "--abbrev-ref", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def dest_branch(refspec: str) -> str:
    ref = refspec.lstrip("+")
    dst = ref.split(":", 1)[1] if ":" in ref else ref
    return dst.removeprefix("refs/heads/")


def check_push(args, directory: str) -> None:
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-f", "--force") or a.startswith("--force-with-lease") or a == "--force-if-includes":
            block("force push is not allowed")
        if a.startswith("-") and not a.startswith("--") and "f" in a[1:]:
            block("force push is not allowed")
        if a in ("--all", "--mirror", "--branches"):
            block("pushing all branches would also push main; push your own branch only")
        if a in PUSH_OPTS_WITH_VALUE:
            i += 2
            continue
        if not a.startswith("-"):
            positional.append(a)
        i += 1
    refspecs = positional[1:]  # first positional is the remote
    for r in refspecs:
        if r.startswith("+"):
            block("force push is not allowed")
    if args and any(a in ("-d", "--delete") for a in args):
        if any(dest_branch(r) in PROTECTED for r in refspecs):
            block("deleting main is not allowed")
    if refspecs:
        branch = None
        for r in refspecs:
            dst = dest_branch(r)
            if dst == "HEAD":
                branch = branch or current_branch(directory)
                dst = branch or ""
            if dst in PROTECTED:
                block("pushing to main is not allowed; push your own branch and open a PR")
        return
    # bare `git push` or `git push <remote>`: pushes the current branch
    if current_branch(directory) in PROTECTED:
        block("you are on main; a bare `git push` would push main. Switch to your issue branch")


def check_bash(cmd: str, cwd: str) -> None:
    for segment in re.split(r"&&|\|\||;|\||\n", cmd):
        tokens = split_tokens(segment.strip())
        # skip leading env assignments such as GIT_TRACE=1
        while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            tokens = tokens[1:]
        if not tokens or os.path.basename(tokens[0]) not in ("git", "git.exe"):
            continue
        directory = cwd
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            opt = tokens[i]
            if opt in GIT_OPTS_WITH_VALUE and i + 1 < len(tokens):
                if opt == "-C":
                    directory = os.path.join(directory, tokens[i + 1])
                i += 2
            else:
                i += 1
        if i < len(tokens) and tokens[i] == "push":
            check_push(tokens[i + 1:], directory)


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
            check_bash(tin.get("command", ""), data.get("cwd") or project_dir)
        elif tool in ("Edit", "Write", "MultiEdit"):
            check_edit(tin.get("file_path", ""), project_dir)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
