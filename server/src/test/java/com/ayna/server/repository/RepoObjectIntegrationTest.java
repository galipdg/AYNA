package com.ayna.server.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.InputStream;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Adding picked elements to the object repository, against a real Neo4j (Testcontainers, needs Docker). */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class RepoObjectIntegrationTest {

	static final String TRIAL_SNAPSHOT_ID = "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b";

	/** The user-name field of the trial app's login window. */
	static final String USER_NAME_INPUT = "e8";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	ObjectMapper mapper;

	String appId;

	String versionId;

	/** Domain nodes only: the migration tool's `__`-prefixed nodes must stay. */
	@BeforeEach
	void setUp() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		appId = createApp("AYNA Trial");
		versionId = createVersion(appId, "1.0");
		importSnapshot(appId, versionId, trialLogin());
	}

	/** SC-10: AutomationId as primary; Name, ControlType and the nearest label as fallback. */
	@Test
	void storesTheObjectAndLinksItToThePickedElementInThatVersion() throws Exception {
		Map<String, Object> fallback = new LinkedHashMap<>();
		fallback.put("name", "Username");
		fallback.put("controlType", "Edit");
		fallback.put("nearestLabel", "Username");

		create(appId, request("login.userNameInput", USER_NAME_INPUT,
				Map.of("automationId", "QApplication.loginWindow.usernameInput"), fallback))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.appId").value(appId))
			.andExpect(jsonPath("$.name").value("login.userNameInput"))
			.andExpect(jsonPath("$.primary.automationId").value("QApplication.loginWindow.usernameInput"))
			.andExpect(jsonPath("$.fallback.nearestLabel").value("Username"))
			.andExpect(jsonPath("$.resolvesTo.length()").value(1))
			.andExpect(jsonPath("$.resolvesTo[0].appVersionId").value(versionId))
			.andExpect(jsonPath("$.resolvesTo[0].snapshotId").value(TRIAL_SNAPSHOT_ID))
			.andExpect(jsonPath("$.resolvesTo[0].snapshotElementId").value(USER_NAME_INPUT))
			.andExpect(jsonPath("$.createdBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.createdAt").isString());

		Record linked = query("""
				MATCH (:Application {id: $a})-[:HAS_OBJECT]->(o:RepoObject {name: 'login.userNameInput'})
				      -[r:RESOLVES_TO]->(e:Element)
				RETURN o.primary AS primary, o.fallback AS fallback, o.createdBy AS createdBy, r.version AS version,
				  e.snapshotId AS snapshotId, e.snapshotElementId AS elementId""").get(0);
		assertThat(linked.get("version").asString()).isEqualTo(versionId);
		assertThat(linked.get("snapshotId").asString()).isEqualTo(TRIAL_SNAPSHOT_ID);
		assertThat(linked.get("elementId").asString()).isEqualTo(USER_NAME_INPUT);
		assertThat(linked.get("createdBy").asString()).isEqualTo(SignedIn.TESTER.userId());
		// Stored as JSON strings in the order the user gave, best first.
		assertThat(linked.get("primary").asString()).isEqualTo("{\"automationId\":\"QApplication.loginWindow.usernameInput\"}");
		assertThat(linked.get("fallback").asString())
			.isEqualTo("{\"name\":\"Username\",\"controlType\":\"Edit\",\"nearestLabel\":\"Username\"}");
	}

	/** SC-11, FR-07: the message names the existing object, and nothing is stored. */
	@Test
	void aLogicalNameTakenInTheApplicationIsAConflict() throws Exception {
		String existing = JsonPath.read(create(appId, userNameInput("login.userNameInput"))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString(), "$.id");

		create(appId, request("login.userNameInput", "e10", Map.of("automationId", "QApplication.loginWindow.passwordInput"),
				null))
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value("The logical name login.userNameInput is already used by repository object "
					+ existing + " in this application"));
		assertThat(count("MATCH (o:RepoObject) RETURN count(o) AS n")).isEqualTo(1);

		// Another application may use the same name.
		String otherApp = createApp("Notepad");
		String otherVersion = createVersion(otherApp, "1.0");
		ObjectNode snapshot = trialLogin();
		snapshot.put("snapshotId", "6f9a1b2c-4d3e-4f70-9bac-2d1e3f4a5b6c");
		importSnapshot(otherApp, otherVersion, snapshot);
		ObjectNode request = userNameInput("login.userNameInput");
		request.put("snapshotId", "6f9a1b2c-4d3e-4f70-9bac-2d1e3f4a5b6c");
		create(otherApp, request).andExpect(status().isCreated());
	}

	/** SC-11: the message shows the expected form; `none.noMatch` is the AI service's "no object fits" (#71). */
	@Test
	void aMalformedOrReservedNameIsRefused() throws Exception {
		create(appId, userNameInput("Login Button")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.name")))
			.andExpect(jsonPath("$.errors[0].message").value(containsString("screen.element")));
		create(appId, userNameInput("none.noMatch")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].message").value(containsString("reserved")));
		create(appId, userNameInput("  ")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.name")));
		assertThat(count("MATCH (o:RepoObject) RETURN count(o) AS n")).isZero();
	}

	@Test
	void everyInvalidPropertyIsReportedAndNothingIsStored() throws Exception {
		Map<String, Object> primary = new LinkedHashMap<>();
		primary.put("automationId", "QApplication.loginWindow.usernameInput");
		primary.put("bounds", List.of(1, 2, 3, 4));
		primary.put("siblingIndex", "first");
		Map<String, Object> fallback = new LinkedHashMap<>();
		fallback.put("automationId", "again");
		fallback.put("name", "");
		fallback.put("colour", "blue");

		create(appId, request("login.userNameInput", USER_NAME_INPUT, primary, fallback)).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(containsInAnyOrder("$.primary.bounds", "$.primary.siblingIndex",
					"$.fallback.automationId", "$.fallback.name", "$.fallback.colour")));

		create(appId, request("login.userNameInput", USER_NAME_INPUT, Map.of(), Map.of("name", "Username")))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.primary")));
		assertThat(count("MATCH (o:RepoObject) RETURN count(o) AS n")).isZero();
	}

	@Test
	void theElementMustComeFromASnapshotOfThisApplication() throws Exception {
		ObjectNode unknownSnapshot = userNameInput("login.userNameInput");
		unknownSnapshot.put("snapshotId", "00000000-0000-4000-8000-000000000000");
		create(appId, unknownSnapshot).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.snapshotId")));

		ObjectNode unknownElement = userNameInput("login.userNameInput");
		unknownElement.put("snapshotElementId", "e99");
		create(appId, unknownElement).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.snapshotElementId")));

		String otherApp = createApp("Notepad");
		create(otherApp, userNameInput("login.userNameInput")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.snapshotId")));

		create("no-such-app", userNameInput("login.userNameInput")).andExpect(status().isNotFound());
		assertThat(count("MATCH (o:RepoObject) RETURN count(o) AS n")).isZero();
	}

	/** The tests API (#39) resolves a step's target among the application's objects. */
	@Test
	void aStepCanTargetTheNewObject() throws Exception {
		create(appId, userNameInput("login.userNameInput")).andExpect(status().isCreated());
		String testId = JsonPath.read(mvc.perform(post("/api/apps/{appId}/tests", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "Login"))))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString(), "$.id");

		mvc.perform(put("/api/tests/{testId}/steps", testId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", "0.1", "steps",
					List.of(Map.of("keyword", "Type", "target", "login.userNameInput", "value", "admin"))))))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.document.steps[0].target").value("login.userNameInput"));
	}

	private ObjectNode userNameInput(String name) {
		return request(name, USER_NAME_INPUT, Map.of("automationId", "QApplication.loginWindow.usernameInput"),
				Map.of("name", "Username"));
	}

	private ObjectNode request(String name, String elementId, Map<String, Object> primary, Map<String, Object> fallback) {
		Map<String, Object> body = new HashMap<>();
		body.put("name", name);
		body.put("snapshotId", TRIAL_SNAPSHOT_ID);
		body.put("snapshotElementId", elementId);
		body.put("primary", primary);
		body.put("fallback", fallback);
		return mapper.valueToTree(body);
	}

	private ResultActions create(String app, JsonNode body) throws Exception {
		return mvc.perform(post("/api/apps/{appId}/repo-objects", app).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(body)));
	}

	private ObjectNode trialLogin() throws Exception {
		try (InputStream in = new ClassPathResource("schemas/examples/snapshot/trial-login.json").getInputStream()) {
			return (ObjectNode) mapper.readTree(in);
		}
	}

	private void importSnapshot(String app, String version, JsonNode document) throws Exception {
		mvc.perform(post("/api/apps/{appId}/versions/{versionId}/snapshots", app, version)
			.contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(document))).andExpect(status().isCreated());
	}

	private String createApp(String name) throws Exception {
		String body = mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name, "technology", "qt"))))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		return JsonPath.read(body, "$.id");
	}

	private String createVersion(String app, String version) throws Exception {
		String body = mvc.perform(post("/api/apps/{appId}/versions", app).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", version))))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		return JsonPath.read(body, "$.id");
	}

	private long count(String cypher) {
		return query(cypher).get(0).get("n").asLong();
	}

	private List<Record> query(String cypher) {
		return driver.executableQuery(cypher).withParameters(Map.of("a", appId)).execute().records();
	}

}
