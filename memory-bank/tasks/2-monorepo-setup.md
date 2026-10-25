# #2 Create monorepo, branch rules and PR template

- Issue: https://github.com/galipdg/AYNA/issues/2
- Owner: omer · Branch: `omer/2-monorepo-setup`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
Most of the repo already existed (folders with `AGENTS.md`, `.github/pull_request_template.md`, `CODEOWNERS`, local guard hook). This issue fills the gaps against the acceptance criteria:
- one short human-facing `README.md` per module folder; build/test details stay in each folder's `AGENTS.md`;
- PR template DoD gets the missing "docs updated" item;
- `main` protection on GitHub (needs the repo owner, see Open issues);
- each member merges one test PR.

## Decisions (small, local to this task)
- 2026-10-25 — READMEs in folders owned by others (`agent/`, `ai/`, `eval/`, `docs/`) are written here because the issue requires them; kept to a purpose paragraph + owner + link to `AGENTS.md` so owners can expand them later.

## Status
- [x] READMEs in agent, client, server, ai, schemas, eval, docs
- [x] PR template: "docs updated" DoD item added (user OK 2026-10-25)
- [ ] `main` protected: PR + 1 approval, no direct pushes (blocked, see Open issues)
- [ ] All three members merged one test PR (galip done; omer: this PR; hasan: asked via his inbox 2026-10-25)
- Next step: push `omer/2-monorepo-setup` and open the PR with `Refs #2` (user OK needed); keep #2 open until protection and hasan's PR are done.

## Manual checks
- 2026-10-25 · omer's agent · `git push origin main` via Claude Code · blocked by `.claude/hooks/guard.sh` · pass (local hook only, not GitHub protection)

## Open issues
- 2026-10-25 — Branch protection cannot be set yet: `galipdg/AYNA` is a private repo on a free personal account (rulesets API: "Upgrade to GitHub Pro or make this repository public"; protection API: 404), and omer has push but not admin. Options: galip enables GitHub Pro via the Student Developer Pack, moves the repo to a free organization with Team/education plan, or makes it public. Until then only the local guard hook stops direct pushes to `main`.
- 2026-10-25 — Retried after galip added omer to the repo: API still reports `admin: false` and `PUT .../branches/main/protection` returns 404. On a personal-account repo collaborators cannot get admin, and protection depends on the **owner's** plan, so omer's GitHub Pro does not help. Real options: (a) galip claims GitHub Pro via the Student Developer Pack (free for students); (b) transfer the repo to omer's account (moves issues; the user-owned "AYNA" Project and repo URL would need relinking); (c) make the repo public.
- 2026-10-25 — This PR uses `Refs #2`, not `Closes #2`, because merging it would auto-close #2 while two criteria are still open.

## Handoff
—

## Outcome (fill when the issue closes)
