# Memory bank

Shared, versioned memory for the three humans and their agents. The rules for reading and writing it are in `/AGENTS.md` §3–§5; this file is the map.

```
memory-bank/
├── project/            stable product knowledge — PR only
│   ├── brief.md        goal, scope, success criteria
│   ├── architecture.md components, data flow, graph model, contracts
│   ├── conventions.md  code style, naming, testing, branches, commits
│   └── glossary.md     project terms
├── decisions/          one ADR per file, never edited after acceptance
│   └── README.md       index of all decisions (one line each)
├── tasks/              one working note per GitHub issue: <issue>-<slug>.md
│   └── _template.md
├── people/
│   ├── galip/  active.md · journal.md · inbox.md
│   ├── omer/   active.md · journal.md · inbox.md
│   └── hasan/  active.md · journal.md · inbox.md
└── learnings.md        gotchas useful to everyone — append only
```

## Why it is shaped like this

Three agents write in parallel on different branches. Every file therefore has exactly one kind of writer, so merges never lose information:

| Kind | Files | Why it does not conflict |
|---|---|---|
| Reviewed | `project/*` | Changes rarely, always through a PR |
| One file per item | `decisions/*`, `tasks/*` | Adding a new file never conflicts |
| Single owner | `people/<id>/active.md`, `journal.md` | Only that person's agent writes it |
| Append only | `people/<id>/inbox.md`, `learnings.md`, `journal.md` | `merge=union` keeps both sides' new lines |

## What does not belong here

- Task status, scope or acceptance criteria → GitHub Issues / Project.
- Facts the code already states (signatures, file lists) → read the code.
- Secrets, credentials, personal data.
