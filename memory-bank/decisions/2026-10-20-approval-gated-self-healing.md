# Self-healing proposes, never applies mid-run

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
A repair applied during a run can make a broken build pass (false pass). TestComplete applies fixes during the run.

## Decision
When an element is not found, the step ends as 'repair proposed' with the top 3 candidates and per-property contributions. The repository changes only after a user approves; the approval becomes a Rule.

## Consequences
Runs may stop more often; false passes are tracked as their own metric (RQ5).
