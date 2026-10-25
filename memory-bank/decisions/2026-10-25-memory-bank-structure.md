# Shared memory bank structure and English as memory language

- Date: 2026-10-25
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
Three agents work in parallel on different branches; a classic single-user memory bank (shared activeContext/progress files) would conflict or lose notes.

## Decision
Every memory file has one kind of writer: reviewed (project/), one file per item (decisions/, tasks/), single owner (people/<id>/active.md, journal.md) or append-only with merge=union (inbox.md, learnings.md, journal.md). AGENTS.md is the entry point; CLAUDE.md imports it so Claude Code always loads it. All memory is written in English.

## Consequences
Agents must follow AGENTS.md §3–§5; a hook blocks edits to other people's private memory.
