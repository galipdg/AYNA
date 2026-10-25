# Client in TypeScript

- Date: 2026-10-25
- Status: Accepted
- Deciders: Galip, Ömerfaruk, Hasan (in person)
- Supersedes: the client language in [Technology stack](2026-10-20-tech-stack.md) ("JavaScript (Electron + React) for the client"); the rest of that ADR stands.

## Context
The tech-stack ADR chose JavaScript for the client. #5 still needed a typed preload API, so the first skeleton used JSDoc types checked by `tsc`. That is TypeScript's type checker with more verbose syntax, and the client was still only a skeleton, so switching was cheap.

## Decision
`client/` is written in TypeScript (`strict`, `.ts` / `.tsx`), still Electron + React + Vite. Type-checked with `tsc -b`, linted with ESLint + typescript-eslint. The rest of the stack is unchanged; TypeScript is the only addition to "no other languages in product code".

## Consequences
The preload/IPC contract is real TypeScript interfaces (`client/src/shared/api.ts`). TypeScript is pinned to 6.0 until typescript-eslint supports 7 (see `learnings.md`).
