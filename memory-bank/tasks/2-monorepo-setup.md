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
- [ ] PR template: add "docs updated" DoD item (`.github/` change, needs user OK)
- [ ] `main` protected: PR + 1 approval, no direct pushes (repo owner galip)
- [ ] All three members merged one test PR (galip done; omer: this PR; hasan: pending)
- Next step: get user OK for the PR template edit, then commit and open the PR.

## Manual checks
- 2026-10-25 · omer's agent · `git push origin main` via Claude Code · blocked by `.claude/hooks/guard.sh` · pass (local hook only, not GitHub protection)

## Open issues
- 2026-10-25 — Branch protection cannot be set yet: `galipdg/AYNA` is a private repo on a free personal account (rulesets API: "Upgrade to GitHub Pro or make this repository public"; protection API: 404), and omer has push but not admin. Options: galip enables GitHub Pro via the Student Developer Pack, moves the repo to a free organization with Team/education plan, or makes it public. Until then only the local guard hook stops direct pushes to `main`.

## Handoff
—

## Outcome (fill when the issue closes)
