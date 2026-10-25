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

Migration notes (2026-10-25): 107 board tasks became issues #2–#108 (PR #1 took number 1), so issue number = board key + 1; titles keep the key, e.g. `[AYNA-021] …` = #22. Owners are labels (`owner:galip|omer|hasan|team`) because teammates were not yet collaborators; assignees are set once they accept the invitation. Weeks are milestones `Week 1` … `Week 14` and `Semester 2`. The empty test task AYNA-108 was not migrated.
