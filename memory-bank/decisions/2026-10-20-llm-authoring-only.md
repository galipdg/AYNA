# Language models only at authoring time

- Date: 2026-10-20
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (advisor informed)

## Context
Agent-style tools that let an LLM choose every action at run time (e.g. UFO) are not repeatable, which is unacceptable for regression testing.

## Decision
The local LLM only suggests steps while a test is written; the user approves them; playback is deterministic and never calls a model. Generated steps may only target objects that exist in the repository.

## Consequences
Everything except NL step generation works without the AI service.
