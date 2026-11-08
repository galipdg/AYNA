package com.ayna.server.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasKey;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import tools.jackson.databind.ObjectMapper;

import com.ayna.server.TestcontainersConfiguration;

/**
 * Accounts, roles, sessions and API tokens with real logins (#60, SC-03), against Neo4j
 * from Testcontainers (needs Docker). Requests here carry no account unless they send a token.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class AuthIntegrationTest {

	static final String ADMIN_PASSWORD = "admin-password-1";

	static final String AYSE_PASSWORD = "ayse-password-1";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	AccountService accounts;

	String adminToken;

	@BeforeEach
	void oneAdmin() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		assertThat(accounts.createFirstAdmin("Admin", ADMIN_PASSWORD)).isTrue();
		adminToken = login("admin", ADMIN_PASSWORD);
	}

	@Test
	void everyApiNeedsAToken() throws Exception {
		mvc.perform(get("/api/apps"))
			.andExpect(status().isUnauthorized())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(header().string(HttpHeaders.WWW_AUTHENTICATE, "Bearer"))
			.andExpect(jsonPath("$.status").value(401))
			.andExpect(jsonPath("$.instance").value("/api/apps"))
			.andExpect(jsonPath("$.detail").value("Log in first: the request has no valid session or API token"));
		mvc.perform(get("/api/apps").header(HttpHeaders.AUTHORIZATION, "Bearer not-a-token"))
			.andExpect(status().isUnauthorized());
		mvc.perform(get("/api/no-such-thing")).andExpect(status().isUnauthorized());
		mvc.perform(get("/api/apps").with(as(adminToken))).andExpect(status().isOk());
	}

	@Test
	void healthLoginAndApiDocsArePublic() throws Exception {
		mvc.perform(get("/api/health")).andExpect(status().isOk());
		mvc.perform(get("/v3/api-docs")).andExpect(status().isOk());
		mvc.perform(get("/swagger-ui/index.html")).andExpect(status().isOk());
	}

	/** `@PublicEndpoint` (the contract) and `SecurityConfig` (the rule) name the same API endpoints. */
	@Test
	void contractShowsExactlyThePublicEndpoints() throws Exception {
		String docs = mvc.perform(get("/v3/api-docs")).andReturn().getResponse().getContentAsString();
		Map<String, Map<String, Map<String, Object>>> paths = JsonPath.read(docs, "$.paths");
		List<String> open = new ArrayList<>();
		paths.forEach((path, operations) -> operations.forEach((method, operation) -> {
			if (List.of().equals(operation.get("security"))) {
				open.add(method.toUpperCase() + " " + path);
			}
		}));
		assertThat(open).containsExactlyInAnyOrder("POST /api/auth/login", "GET /api/health");
		assertThat((List<?>) JsonPath.read(docs, "$.security[*].bearerAuth")).hasSize(1);
	}

	@Test
	void wrongPasswordAndUnknownUserGetTheSameAnswer() throws Exception {
		for (String[] attempt : new String[][] { { "admin", "wrong-password" }, { "nobody", ADMIN_PASSWORD },
				{ "admin", null } }) {
			loginRequest(attempt[0], attempt[1]).andExpect(status().isUnauthorized())
				.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
				.andExpect(jsonPath("$.detail").value("Wrong user name or password"));
		}
	}

	@Test
	void loginReturnsTheUserAndAnExpiry() throws Exception {
		loginRequest("ADMIN", ADMIN_PASSWORD).andExpect(status().isOk())
			.andExpect(jsonPath("$.token").isString())
			.andExpect(jsonPath("$.expiresAt").isString())
			.andExpect(jsonPath("$.user.username").value("admin"))
			.andExpect(jsonPath("$.user.role").value("admin"))
			.andExpect(jsonPath("$.user", not(hasKey("passwordHash"))));
		mvc.perform(get("/api/auth/me").with(as(adminToken)))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.username").value("admin"));
	}

	/** SC-03: the admin creates ayse, ayse edits a test, the server stores who did it. */
	@Test
	void aTesterIsRecordedOnHerEditsAndCannotManageUsers() throws Exception {
		createUser("ayse", AYSE_PASSWORD, "tester").andExpect(status().isCreated())
			.andExpect(jsonPath("$.username").value("ayse"))
			.andExpect(jsonPath("$.role").value("tester"));
		String ayse = login("ayse", AYSE_PASSWORD);

		String appId = id(mvc.perform(post("/api/apps").with(as(ayse))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"Sample\", \"technology\": \"uia\"}")).andExpect(status().isCreated()));
		String testId = id(mvc.perform(post("/api/apps/" + appId + "/tests").with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"Login\"}"))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.createdBy.username").value("admin")));
		mvc.perform(put("/api/tests/" + testId + "/steps").with(as(ayse))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"version\": \"0.1\", \"steps\": []}"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.createdBy.username").value("admin"))
			.andExpect(jsonPath("$.updatedBy.username").value("ayse"))
			.andExpect(jsonPath("$.updatedAt").isString());

		mvc.perform(get("/api/users").with(as(ayse)))
			.andExpect(status().isForbidden())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value("Only admins may do this"));
		mvc.perform(post("/api/users").with(as(ayse))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"username\": \"mallory\", \"password\": \"long-enough\", \"role\": \"admin\"}"))
			.andExpect(status().isForbidden());
	}

	@Test
	void passwordsAreStoredAsBcryptHashes() throws Exception {
		createUser("ayse", AYSE_PASSWORD, "tester").andExpect(status().isCreated());
		String hash = driver.executableQuery("MATCH (u:User {username: 'ayse'}) RETURN u.passwordHash AS h")
			.execute()
			.records()
			.get(0)
			.get("h")
			.asString();
		assertThat(hash).startsWith("$2a$10$").doesNotContain(AYSE_PASSWORD);
		mvc.perform(get("/api/users").with(as(adminToken)))
			.andExpect(jsonPath("$[*].username").value(contains("admin", "ayse")))
			.andExpect(jsonPath("$[0]", not(hasKey("passwordHash"))));
	}

	@Test
	void invalidAccountsAreRejected() throws Exception {
		createUser("ayse", "short", "tester").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.password"));
		createUser("ayse", "x".repeat(73), "tester").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.password"));
		createUser("ayşe", AYSE_PASSWORD, "tester").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.username"));
		createUser("ayse", AYSE_PASSWORD, "root").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.role"));
		createUser("ayse", AYSE_PASSWORD, "tester").andExpect(status().isCreated());
		createUser("AYSE", AYSE_PASSWORD, "tester").andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value("User name already taken: ayse"));
	}

	@Test
	void logoutAndExpiryEndASession() throws Exception {
		mvc.perform(post("/api/auth/logout").with(as(adminToken))).andExpect(status().isNoContent());
		mvc.perform(get("/api/apps").with(as(adminToken))).andExpect(status().isUnauthorized());

		String token = login("admin", ADMIN_PASSWORD);
		driver.executableQuery("MATCH (t:AuthToken {kind: 'session'}) SET t.expiresAt = datetime() - duration('PT1S')")
			.execute();
		mvc.perform(get("/api/apps").with(as(token))).andExpect(status().isUnauthorized());
	}

	@Test
	void aNewPasswordEndsSessionsAndARoleChangeTakesEffectAtOnce() throws Exception {
		String ayseId = id(createUser("ayse", AYSE_PASSWORD, "tester"));
		String ayse = login("ayse", AYSE_PASSWORD);

		mvc.perform(patch("/api/users/" + ayseId).with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"role\": \"admin\"}")).andExpect(status().isOk()).andExpect(jsonPath("$.role").value("admin"));
		mvc.perform(get("/api/users").with(as(ayse))).andExpect(status().isOk());

		mvc.perform(patch("/api/users/" + ayseId).with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"password\": \"another-password\"}")).andExpect(status().isOk());
		mvc.perform(get("/api/apps").with(as(ayse))).andExpect(status().isUnauthorized());
		loginRequest("ayse", AYSE_PASSWORD).andExpect(status().isUnauthorized());
		login("ayse", "another-password");

		mvc.perform(patch("/api/users/" + ayseId).with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{}")).andExpect(status().isBadRequest());
	}

	@Test
	void theLastAdminStays() throws Exception {
		String adminId = JsonPath.read(mvc.perform(get("/api/auth/me").with(as(adminToken)))
			.andReturn()
			.getResponse()
			.getContentAsString(), "$.id");
		mvc.perform(patch("/api/users/" + adminId).with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"role\": \"tester\"}"))
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value("The last admin cannot become a tester"));
		mvc.perform(delete("/api/users/" + adminId).with(as(adminToken)))
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value("The last admin cannot be removed"));
		assertThat(accounts.createFirstAdmin("second", ADMIN_PASSWORD)).isFalse();
	}

	@Test
	void aRemovedAccountCannotLogInButKeepsItsNameOnItsEdits() throws Exception {
		String ayseId = id(createUser("ayse", AYSE_PASSWORD, "tester"));
		String ayse = login("ayse", AYSE_PASSWORD);
		String appId = id(mvc.perform(post("/api/apps").with(as(ayse))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"Sample\", \"technology\": \"uia\"}")));
		String testId = id(mvc.perform(post("/api/apps/" + appId + "/tests").with(as(ayse))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"Login\"}")));

		mvc.perform(delete("/api/users/" + ayseId).with(as(adminToken))).andExpect(status().isNoContent());

		mvc.perform(get("/api/apps").with(as(ayse))).andExpect(status().isUnauthorized());
		loginRequest("ayse", AYSE_PASSWORD).andExpect(status().isUnauthorized());
		mvc.perform(get("/api/users").with(as(adminToken))).andExpect(jsonPath("$[*].username").value(contains("admin")));
		mvc.perform(get("/api/tests/" + testId).with(as(adminToken)))
			.andExpect(jsonPath("$.createdBy.id").value(ayseId))
			.andExpect(jsonPath("$.createdBy.username").value("ayse"));
		mvc.perform(delete("/api/users/" + ayseId).with(as(adminToken))).andExpect(status().isNotFound());
		createUser("ayse", AYSE_PASSWORD, "tester").andExpect(status().isConflict());
	}

	/** FR-23: the CLI runner sends a CI account's API token as a Bearer token. */
	@Test
	void anApiTokenWorksUntilRevokedAndIsShownOnlyOnce() throws Exception {
		String ciId = id(createUser("ci", "ci-password-1", "tester"));
		ResultActions created = mvc.perform(post("/api/users/" + ciId + "/tokens").with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"Jenkins\"}"))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.name").value("Jenkins"))
			.andExpect(jsonPath("$.token").isString());
		String body = created.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
		String token = JsonPath.read(body, "$.token");
		String tokenId = JsonPath.read(body, "$.id");

		mvc.perform(get("/api/auth/me").with(as(token))).andExpect(jsonPath("$.username").value("ci"));
		mvc.perform(get("/api/users/" + ciId + "/tokens").with(as(adminToken)))
			.andExpect(jsonPath("$[*].name").value(contains("Jenkins")))
			.andExpect(jsonPath("$[0]", not(hasKey("token"))))
			.andExpect(jsonPath("$[0]", not(hasKey("tokenHash"))));
		mvc.perform(post("/api/auth/logout").with(as(token))).andExpect(status().isNoContent());
		mvc.perform(get("/api/auth/me").with(as(token))).andExpect(status().isOk());

		mvc.perform(delete("/api/tokens/" + tokenId).with(as(adminToken))).andExpect(status().isNoContent());
		mvc.perform(get("/api/auth/me").with(as(token))).andExpect(status().isUnauthorized());
		mvc.perform(delete("/api/tokens/" + tokenId).with(as(adminToken))).andExpect(status().isNotFound());
		mvc.perform(post("/api/users/" + ciId + "/tokens").with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \" \"}")).andExpect(status().isBadRequest());
	}

	private ResultActions loginRequest(String username, String password) throws Exception {
		Map<String, String> body = new HashMap<>();
		body.put("username", username);
		body.put("password", password);
		return mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
			.content(new ObjectMapper().writeValueAsString(body)));
	}

	private String login(String username, String password) throws Exception {
		return JsonPath.read(loginRequest(username, password).andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString(), "$.token");
	}

	private ResultActions createUser(String username, String password, String role) throws Exception {
		return mvc.perform(post("/api/users").with(as(adminToken))
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"username\": \"" + username + "\", \"password\": \"" + password + "\", \"role\": \"" + role
					+ "\"}"));
	}

	private static String id(ResultActions result) throws Exception {
		return JsonPath.read(result.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8), "$.id");
	}

	private static RequestPostProcessor as(String token) {
		return request -> {
			request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer " + token);
			return request;
		};
	}

}
