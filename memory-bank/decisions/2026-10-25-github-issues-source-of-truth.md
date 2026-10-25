# GitHub Issues + Project as the task source of truth

- Date: 2026-10-25
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
Agents could not read the earlier claude.ai board. Status and acceptance criteria must be readable and updatable by humans and agents alike.

## Decision
Every task is a GitHub issue with acceptance criteria as a checklist, a week milestone, area labels and an assignee. The 'AYNA' GitHub Project (Team planning template) shows the board. PRs close issues with 'Closes #n'. Memory links issues instead of copying them.

## Consequences
The claude.ai AYNA Board becomes read-only history after the migration.
