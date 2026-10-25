# Learnings

Append-only. Non-obvious things learned the hard way that help everyone. Format:
`- YYYY-MM-DD · <id> · <area> · <what happened> → <what to do instead>`

- 2026-10-25 · galip · github · `gh project ...` failed: the default gh token has no Projects scope → run `gh auth refresh -s project` once (browser approval), then move cards with `gh project item-edit` (AYNA board = project 1, owner galipdg, field "Status": Todo / In progress / Done).
- 2026-10-25 · omer · server · Spring Boot 4 moved test annotations to per-module packages: `AutoConfigureMockMvc` is `org.springframework.boot.webmvc.test.autoconfigure`, and start.spring.io names the web starter `spring-boot-starter-webmvc` → check Boot 4 package names before copying Boot 3 examples.
- 2026-10-25 · galip · github · `gh pr edit` fails with "Projects (classic) is being deprecated" (GraphQL `projectCards`) → update the PR with `gh api -X PATCH repos/galipdg/AYNA/pulls/<n> -F body=@file.md` instead.
- 2026-10-25 · galip · agent · pywinauto 0.6.9's `Desktop(backend="uia").windows()` defaults to `visible_only=False` (unlike `find_elements`), and `UIAElementInfo` properties turn COM errors into `None`/`""`, so a failed read looks like an empty AutomationId or Name → pass `visible_only=True`, and read `element_info.element.Current*` when you need to tell "empty" from "failed". PyPI also has a 1.0.0b1 pre-release (2026-10-15); pin `pywinauto==0.6.9` until we test 1.0.
