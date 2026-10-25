# Learnings

Append-only. Non-obvious things learned the hard way that help everyone. Format:
`- YYYY-MM-DD · <id> · <area> · <what happened> → <what to do instead>`

- 2026-10-25 · omer · server · Spring Boot 4 moved test annotations to per-module packages: `AutoConfigureMockMvc` is `org.springframework.boot.webmvc.test.autoconfigure`, and start.spring.io names the web starter `spring-boot-starter-webmvc` → check Boot 4 package names before copying Boot 3 examples.
