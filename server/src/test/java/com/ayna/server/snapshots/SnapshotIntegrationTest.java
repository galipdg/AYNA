package com.ayna.server.snapshots;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.ZonedDateTime;
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
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.TestcontainersConfiguration;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Snapshot import against a real Neo4j started by Testcontainers (needs Docker). */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class SnapshotIntegrationTest {

	static final String TRIAL_SNAPSHOT_ID = "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b";

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
	}

	@Test
	void importsTheTrialAppSnapshotAsOneWindowAndFourteenElements() throws Exception {
		importSnapshot(appId, versionId, SnapshotSchemaTest.trialLogin()).andExpect(status().isCreated())
			.andExpect(jsonPath("$.snapshotId").value(TRIAL_SNAPSHOT_ID))
			.andExpect(jsonPath("$.appVersionId").value(versionId))
			.andExpect(jsonPath("$.name").value("AYNA Trial - Login"))
			.andExpect(jsonPath("$.className").value("LoginWindow"))
			.andExpect(jsonPath("$.elementCount").value(14));

		assertThat(count("MATCH (:AppVersion {id: $v})-[:HAS_WINDOW]->(w:Window) RETURN count(w) AS n")).isEqualTo(1);
		assertThat(count("MATCH (e:Element {snapshotId: $s}) RETURN count(e) AS n")).isEqualTo(14);
		assertThat(count("MATCH (:Element {snapshotId: $s})-[c:CONTAINS]->(:Element) RETURN count(c) AS n"))
			.isEqualTo(13);
		// The window holds only its root element; the rest hang below it as in the snapshot.
		assertThat(query("""
				MATCH (:Window {snapshotId: $s})-[:CONTAINS]->(e:Element)
				RETURN e.snapshotElementId AS id""").stream().map(r -> r.get("id").asString()).toList())
			.containsExactly("e0");
		assertThat(count("""
				MATCH (:AppVersion {id: $v})-[:HAS_WINDOW]->(:Window)-[:CONTAINS]->(:Element {snapshotElementId: 'e0'})
				      -[:CONTAINS]->(:Element {snapshotElementId: 'e1'})-[:CONTAINS]->(:Element {snapshotElementId: 'e2'})
				      -[:CONTAINS]->(e:Element {snapshotElementId: 'e3', controlType: 'MenuItem'})
				RETURN count(e) AS n""")).isEqualTo(1);
		assertThat(count("""
				MATCH (:Element {snapshotElementId: 'e0', snapshotId: $s})-[:CONTAINS]->(e:Element)
				RETURN count(e) AS n""")).isEqualTo(8);
	}

	@Test
	void storesTheDescriptorAndTheWindowProperties() throws Exception {
		importSnapshot(appId, versionId, SnapshotSchemaTest.trialLogin()).andExpect(status().isCreated());

		Map<String, Object> button = query("""
				MATCH (e:Element {snapshotId: $s, automationId: 'QApplication.loginWindow.loginButton'})
				RETURN properties(e) AS p""").get(0).get("p").asMap();
		assertThat(button).containsEntry("controlType", "Button")
			.containsEntry("name", "Login")
			.containsEntry("snapshotElementId", "e12")
			.containsEntry("enabled", true)
			.containsEntry("frameworkId", "Qt")
			.containsKeys("id", "bounds", "dpi", "siblingIndex", "parentPath");
		assertThat(button.get("bounds")).isInstanceOf(List.class);
		assertThat((List<?>) button.get("bounds")).hasSize(4).allSatisfy(n -> assertThat(n).isInstanceOf(Long.class));

		Map<String, Object> window = query("MATCH (w:Window {snapshotId: $s}) RETURN properties(w) AS p").get(0)
			.get("p")
			.asMap();
		assertThat(window).containsEntry("name", "AYNA Trial - Login")
			.containsEntry("className", "LoginWindow")
			.containsEntry("featureVersion", "features-v0")
			.containsEntry("exeName", "python.exe")
			.containsEntry("fileVersion", "3.13.150.1013")
			.doesNotContainKeys("handle", "processId");
		assertThat(window.get("capturedAt")).isInstanceOf(ZonedDateTime.class);
		assertThat(((ZonedDateTime) window.get("capturedAt")).toOffsetDateTime().toString())
			.isEqualTo("2026-10-31T17:42:19+03:00");
	}

	@Test
	void reimportingTheSameSnapshotIdIntoTheSameVersionChangesNothing() throws Exception {
		String first = importSnapshot(appId, versionId, SnapshotSchemaTest.trialLogin()).andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		long nodes = count("MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__') RETURN count(n) AS n");
		long relationships = count("MATCH ()-[r]->() RETURN count(r) AS n");

		// Even a changed body is not imported again: the snapshot id is the identity (FR-04).
		ObjectNode changed = SnapshotSchemaTest.trialLogin();
		((ObjectNode) changed.get("window")).put("title", "Something else");
		String second = importSnapshot(appId, versionId, changed).andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();

		assertThat(second).isEqualTo(first);
		assertThat(count("MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__') RETURN count(n) AS n"))
			.isEqualTo(nodes);
		assertThat(count("MATCH ()-[r]->() RETURN count(r) AS n")).isEqualTo(relationships);
	}

	@Test
	void theSameSnapshotIdInAnotherVersionIsAConflict() throws Exception {
		importSnapshot(appId, versionId, SnapshotSchemaTest.trialLogin()).andExpect(status().isCreated());
		String otherVersion = createVersion(appId, "1.1");

		importSnapshot(appId, otherVersion, SnapshotSchemaTest.trialLogin()).andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value("Snapshot " + TRIAL_SNAPSHOT_ID
					+ " was already imported into version " + versionId));
		assertThat(count("MATCH (w:Window) RETURN count(w) AS n")).isEqualTo(1);
	}

	@Test
	void anInvalidSnapshotIsRejectedAndNothingIsWritten() throws Exception {
		ObjectNode document = SnapshotSchemaTest.trialLogin();
		document.put("version", "0.2");
		((ObjectNode) document.get("elements").get(13)).put("parentId", "e1");

		importSnapshot(appId, versionId, document).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.version")));

		document.put("version", "0.1");
		importSnapshot(appId, versionId, document).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.elements[13].parentId")));

		assertThat(count("MATCH (n:Window|Element) RETURN count(n) AS n")).isZero();
	}

	@Test
	void anUnknownApplicationOrAVersionOfAnotherApplicationIsNotFound() throws Exception {
		String otherApp = createApp("Notepad");
		String otherVersion = createVersion(otherApp, "1.0");

		importSnapshot("no-such-app", versionId, SnapshotSchemaTest.trialLogin()).andExpect(status().isNotFound());
		importSnapshot(appId, otherVersion, SnapshotSchemaTest.trialLogin()).andExpect(status().isNotFound());
		importSnapshot(appId, "no-such-version", SnapshotSchemaTest.trialLogin()).andExpect(status().isNotFound());
		assertThat(count("MATCH (n:Window|Element) RETURN count(n) AS n")).isZero();
	}

	private ResultActions importSnapshot(String app, String version, JsonNode document) throws Exception {
		return mvc.perform(post("/api/apps/{appId}/versions/{versionId}/snapshots", app, version)
			.contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(document)));
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
		return driver.executableQuery(cypher)
			.withParameters(Map.of("v", versionId, "s", TRIAL_SNAPSHOT_ID))
			.execute()
			.records();
	}

}
