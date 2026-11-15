package com.ayna.server.auth;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Import;

import com.ayna.server.TestcontainersConfiguration;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.ObjectMapper;

/**
 * The run report read over a real HTTP connection with a real bearer token (#245). The report
 * is a `StreamingResponseBody`, finished on an ASYNC dispatch that MockMvc only runs when a
 * test asks for it, and then with the test's security context instead of the token's. Here
 * the servlet container runs that dispatch as it does in production.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfiguration.class)
class RunReportOverHttpIntegrationTest {

	static final String PASSWORD = "admin-password-1";

	@LocalServerPort
	int port;

	@Autowired
	Driver driver;

	@Autowired
	AccountService accounts;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	StepSchema stepSchema;

	final HttpClient http = HttpClient.newHttpClient();

	String token;

	@BeforeEach
	void signedInAdmin() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		assertThat(accounts.createFirstAdmin("Admin", PASSWORD)).isTrue();
		token = JsonPath.read(send("POST", "/api/auth/login", Map.of("username", "admin", "password", PASSWORD), null)
			.body(), "$.token");
	}

	@Test
	void aSignedInClientReadsTheWholeReport() throws Exception {
		String runId = aRunWithSteps(3);

		HttpResponse<String> report = send("GET", "/api/runs/" + runId + "/report.html", null, token);

		assertThat(report.statusCode()).isEqualTo(200);
		assertThat(report.body()).startsWith("<!DOCTYPE html>")
			.contains("<tbody id=\"step-3\"")
			.endsWith("</html>\n");
	}

	@Test
	void theReportStillNeedsAToken() throws Exception {
		String runId = aRunWithSteps(1);

		HttpResponse<String> report = send("GET", "/api/runs/" + runId + "/report.html", null, null);

		assertThat(report.statusCode()).isEqualTo(401);
		assertThat(report.body()).doesNotContain("<html");
	}

	@Test
	void theScreenshotStillNeedsAToken() throws Exception {
		String runId = aRunWithSteps(1);

		assertThat(send("GET", "/api/runs/" + runId + "/results/0/screenshot", null, null).statusCode())
			.isEqualTo(401);
	}

	/** A started run of a test with `steps` clicks, made through the API as the signed-in admin. */
	private String aRunWithSteps(int steps) throws Exception {
		String appId = id(send("POST", "/api/apps", Map.of("name", "Müşteri Kayıt", "technology", "PySide6"), token));
		String versionId = id(send("POST", "/api/apps/" + appId + "/versions", Map.of("version", "1.0.0"), token));
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: 'login.loginButton'})""")
			.withParameters(Map.of("appId", appId))
			.execute();
		String testId = id(send("POST", "/api/apps/" + appId + "/tests", Map.of("name", "Giriş"), token));
		Map<String, Object> click = Map.of("keyword", "Click", "target", "login.loginButton");
		HttpResponse<String> saved = send("PUT", "/api/tests/" + testId + "/steps",
				Map.of("version", stepSchema.version(), "steps", Collections.nCopies(steps, click)), token);
		assertThat(saved.statusCode()).isEqualTo(200);
		List<String> stepIds = JsonPath.read(saved.body(), "$.document.steps[*].id");
		assertThat(stepIds).hasSize(steps);
		return id(send("POST", "/api/runs", Map.of("testId", testId, "appVersionId", versionId), token));
	}

	private HttpResponse<String> send(String method, String path, Object body, String bearer) throws Exception {
		HttpRequest.Builder request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + path))
			.method(method, body == null ? HttpRequest.BodyPublishers.noBody()
					: HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)));
		if (body != null) {
			request.header("Content-Type", "application/json");
		}
		if (bearer != null) {
			request.header("Authorization", "Bearer " + bearer);
		}
		return http.send(request.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
	}

	private static String id(HttpResponse<String> created) {
		assertThat(created.statusCode()).as(created.body()).isEqualTo(201);
		return JsonPath.read(created.body(), "$.id");
	}

}
