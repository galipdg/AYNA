package com.ayna.server.tests;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Tests and steps API against a real Neo4j started by Testcontainers (needs Docker). */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class TestIntegrationTest {

	static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	StepSchema schema;

	String appId;

	/** Domain nodes only: the migration tool's `__`-prefixed nodes must stay. */
	@BeforeEach
	void setUp() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		appId = createApp("Müşteri Kayıt");
		repoObjects(appId, "login.userNameInput", "login.passwordInput", "login.loginButton", "main.statusLabel");
	}

	@Test
	void createsAnEmptyTest() throws Exception {
		createTest(appId, "Giriş başarılı").andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(matchesPattern(UUID_PATTERN)))
			.andExpect(jsonPath("$.appId").value(appId))
			.andExpect(jsonPath("$.name").value("Giriş başarılı"))
			.andExpect(jsonPath("$.document.version").value(schema.version()))
			.andExpect(jsonPath("$.document.steps.length()").value(0))
			.andExpect(jsonPath("$.createdBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.updatedBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.createdAt").isString())
			.andExpect(header().string("Location", matchesPattern("/api/tests/" + UUID_PATTERN)));
	}

	@Test
	void listsTestsOfOneApplicationSortedByName() throws Exception {
		String other = createApp("Notepad");
		String b = id(createTest(appId, "B testi"));
		createTest(appId, "A testi");
		createTest(other, "C testi");
		replaceSteps(b, steps(click("login.loginButton"), click("login.loginButton"))).andExpect(status().isOk());

		mvc.perform(get("/api/apps/{id}/tests", appId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[*].name").value(contains("A testi", "B testi")))
			.andExpect(jsonPath("$[1].stepCount").value(2));
	}

	@Test
	void duplicateNameInTheSameApplicationIsAConflict() throws Exception {
		createTest(appId, "Giriş").andExpect(status().isCreated());
		createTest(appId, "Giriş").andExpect(status().isConflict())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value(containsString("Giriş")));
		createTest(createApp("Notepad"), "Giriş").andExpect(status().isCreated());
	}

	@Test
	void unknownApplicationOrTestIsNotFound() throws Exception {
		String unknown = "00000000-0000-0000-0000-000000000000";
		createTest(unknown, "x").andExpect(status().isNotFound());
		mvc.perform(get("/api/apps/{id}/tests", unknown)).andExpect(status().isNotFound());
		mvc.perform(get("/api/tests/{id}", unknown)).andExpect(status().isNotFound());
		replaceSteps(unknown, steps()).andExpect(status().isNotFound());
		mvc.perform(delete("/api/tests/{id}", unknown)).andExpect(status().isNotFound());
	}

	@Test
	void savesStepsWithIdsAndReadsThemBackUnchanged() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		List<Map<String, Object>> written = steps(
				Map.of("keyword", "Type", "target", "login.userNameInput", "value", "ömer ğüşıİç"),
				Map.of("keyword", "Click", "target", "login.loginButton", "timeoutMs", 15000),
				Map.of("keyword", "Verify", "target", "main.statusLabel", "checkpoint",
						Map.of("property", "name", "operator", "contains", "expected", "Hoş geldiniz")));

		JsonNode saved = body(replaceSteps(testId, written).andExpect(status().isOk()));
		JsonNode read = body(mvc.perform(get("/api/tests/{id}", testId)).andExpect(status().isOk()));

		assertThat(read).isEqualTo(saved);
		JsonNode steps = read.get("document").get("steps");
		assertThat(steps).hasSize(3).allSatisfy(s -> assertThat(s.get("id").asString()).matches(UUID_PATTERN));
		assertThat(withoutIds(steps)).isEqualTo(mapper.valueToTree(written));
	}

	@Test
	void reorderKeepsStepIds() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		JsonNode first = body(replaceSteps(testId,
				steps(type("login.userNameInput", "a"), type("login.passwordInput", "b"), click("login.loginButton"))));
		List<String> ids = ids(first);

		JsonNode reordered = body(replaceSteps(testId, steps(withId(ids.get(2), click("login.loginButton")),
				withId(ids.get(0), type("login.userNameInput", "a")), withId(ids.get(1), type("login.passwordInput", "b"))))
			.andExpect(status().isOk()));

		assertThat(ids(reordered)).containsExactly(ids.get(2), ids.get(0), ids.get(1));
		assertThat(stepNodes()).isEqualTo(3);
	}

	@Test
	void stepsLeftOutAreDeletedAndEditedStepsKeepTheirNode() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		List<String> ids = ids(body(replaceSteps(testId,
				steps(type("login.userNameInput", "a"), click("login.loginButton"),
						Map.of("keyword", "Click", "target", "login.loginButton", "timeoutMs", 5000)))));

		JsonNode after = body(replaceSteps(testId,
				steps(withId(ids.get(0), type("login.passwordInput", "yeni")), click("main.statusLabel")))
			.andExpect(status().isOk()));

		JsonNode steps = after.get("document").get("steps");
		assertThat(steps.get(0).get("id").asString()).isEqualTo(ids.get(0));
		assertThat(steps.get(0).get("target").asString()).isEqualTo("login.passwordInput");
		assertThat(steps.get(0).get("value").asString()).isEqualTo("yeni");
		assertThat(ids(after)).doesNotContain(ids.get(1), ids.get(2));
		assertThat(stepNodes()).isEqualTo(2);
	}

	@Test
	void editingAStepDropsFieldsItNoLongerHas() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		String stepId = ids(body(replaceSteps(testId,
				steps(Map.of("keyword", "Click", "target", "login.loginButton", "timeoutMs", 5000))))).get(0);

		JsonNode after = body(replaceSteps(testId, steps(withId(stepId, click("login.loginButton")))));

		assertThat(after.get("document").get("steps").get(0).has("timeoutMs")).isFalse();
	}

	@Test
	void invalidStepIsRejectedWithTheFailingFieldPath() throws Exception {
		String testId = id(createTest(appId, "Giriş"));

		replaceSteps(testId, steps(click("login.loginButton"), Map.of("keyword", "Type", "target", "login.userNameInput")))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.detail").value(containsString(schema.version())))
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.steps[1].value")));
		replaceSteps(testId, steps(Map.of("keyword", "Click", "target", "login.loginButton", "value", "x")))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.steps[0].value")))
			.andExpect(jsonPath("$.errors[0].message").value("'value' is not allowed here"));
		mvc.perform(put("/api/tests/{id}/steps", testId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"version\": \"0.0\", \"steps\": []}")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.version"));

		assertThat(stepNodes()).isZero();
	}

	@Test
	void unknownTargetIsRejectedWithItsPath() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		String otherApp = createApp("Notepad");
		repoObjects(otherApp, "main.saveButton");

		replaceSteps(testId, steps(click("login.loginButton"), click("main.saveButton")))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.steps[1].target"))
			.andExpect(jsonPath("$.errors[0].message").value(containsString("main.saveButton")));
		assertThat(stepNodes()).isZero();
	}

	@Test
	void stepIdOfAnotherTestOrRepeatedIdIsRejected() throws Exception {
		String testA = id(createTest(appId, "A"));
		String testB = id(createTest(appId, "B"));
		String stepOfA = ids(body(replaceSteps(testA, steps(click("login.loginButton"))))).get(0);

		replaceSteps(testB, steps(withId(stepOfA, click("login.loginButton")))).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.steps[0].id"));
		replaceSteps(testA, steps(withId(stepOfA, click("login.loginButton")), withId(stepOfA, click("login.loginButton"))))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.steps[1].id"));
		assertThat(ids(body(mvc.perform(get("/api/tests/{id}", testA))))).containsExactly(stepOfA);
	}

	@Test
	void renamesATest() throws Exception {
		String testId = id(createTest(appId, "Eski"));
		createTest(appId, "Dolu");

		mvc.perform(patch("/api/tests/{id}", testId).contentType(MediaType.APPLICATION_JSON).content("{\"name\": \"Yeni\"}"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.name").value("Yeni"));
		mvc.perform(patch("/api/tests/{id}", testId).contentType(MediaType.APPLICATION_JSON).content("{\"name\": \"Dolu\"}"))
			.andExpect(status().isConflict());
		mvc.perform(patch("/api/tests/{id}", testId).contentType(MediaType.APPLICATION_JSON).content("{\"name\": \"Yeni\"}"))
			.andExpect(status().isOk());
	}

	@Test
	void deletesATestWithItsStepsButNotTheRepositoryObjects() throws Exception {
		String testId = id(createTest(appId, "Giriş"));
		replaceSteps(testId, steps(click("login.loginButton"), click("login.loginButton")));

		mvc.perform(delete("/api/tests/{id}", testId)).andExpect(status().isNoContent());

		mvc.perform(get("/api/tests/{id}", testId)).andExpect(status().isNotFound());
		assertThat(stepNodes()).isZero();
		assertThat(count("MATCH (o:RepoObject) RETURN count(o) AS n")).isEqualTo(4);
	}

	@Test
	void exportThenImportGivesAnIdenticalTest() throws Exception {
		String testId = id(createTest(appId, "Giriş başarılı"));
		replaceSteps(testId, steps(type("login.userNameInput", "admin"), type("login.passwordInput", "şifre"),
				Map.of("keyword", "Click", "target", "login.loginButton", "timeoutMs", 3000),
				Map.of("keyword", "Verify", "target", "main.statusLabel", "checkpoint",
						Map.of("property", "visible", "operator", "equals", "expected", true))));

		ResultActions exported = mvc.perform(get("/api/tests/{id}/export", testId)).andExpect(status().isOk())
			.andExpect(header().string("Content-Disposition", containsString("attachment")));
		JsonNode file = body(exported);
		assertThat(file.get("format").asString()).isEqualTo("ayna-test");
		assertThat(file.get("document").get("steps").get(0).has("id")).isFalse();

		mvc.perform(delete("/api/tests/{id}", testId)).andExpect(status().isNoContent());
		String imported = id(importTest(appId, file.toString()).andExpect(status().isCreated()));

		assertThat(imported).isNotEqualTo(testId);
		assertThat(body(mvc.perform(get("/api/tests/{id}/export", imported)))).isEqualTo(file);
	}

	@Test
	void importRejectsOtherFilesAndNamesTheFailingField() throws Exception {
		importTest(appId, "{\"format\": \"other\", \"name\": \"x\", \"document\": {}}").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.format"));
		importTest(appId, "{\"format\": \"ayna-test\", \"name\": \"x\", \"document\": {\"version\": \"%s\", \"steps\": [{\"keyword\": \"Click\", \"target\": \"main.nothing\"}]}}"
			.formatted(schema.version())).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.document.steps[0].target"));
		importTest(appId, "{\"format\": \"ayna-test\", \"name\": \"x\"}").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.document"));

		assertThat(count("MATCH (t:TestCase) RETURN count(t) AS n")).isZero();
	}

	// --- helpers --------------------------------------------------------------------------

	private String createApp(String name) throws Exception {
		return id(mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name, "technology", "uia")))));
	}

	/** The repository API is #25; until then the tests create objects directly. */
	private void repoObjects(String app, String... names) {
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				UNWIND $names AS name
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: name})""")
			.withParameters(Map.of("appId", app, "names", List.of(names)))
			.execute();
	}

	private ResultActions createTest(String app, String name) throws Exception {
		return mvc.perform(post("/api/apps/{id}/tests", app).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name))));
	}

	private ResultActions replaceSteps(String testId, List<Map<String, Object>> steps) throws Exception {
		return mvc.perform(put("/api/tests/{id}/steps", testId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", schema.version(), "steps", steps))));
	}

	private ResultActions importTest(String app, String body) throws Exception {
		return mvc.perform(post("/api/apps/{id}/tests/import", app).contentType(MediaType.APPLICATION_JSON).content(body));
	}

	@SafeVarargs
	private static List<Map<String, Object>> steps(Map<String, Object>... steps) {
		return List.of(steps);
	}

	private static Map<String, Object> click(String target) {
		return Map.of("keyword", "Click", "target", target);
	}

	private static Map<String, Object> type(String target, String value) {
		return Map.of("keyword", "Type", "target", target, "value", value);
	}

	private static Map<String, Object> withId(String id, Map<String, Object> step) {
		Map<String, Object> copy = new java.util.HashMap<>(step);
		copy.put("id", id);
		return copy;
	}

	private JsonNode body(ResultActions result) throws Exception {
		return mapper.readTree(result.andReturn().getResponse().getContentAsString());
	}

	private static String id(ResultActions result) throws Exception {
		return JsonPath.read(result.andReturn().getResponse().getContentAsString(), "$.id");
	}

	private static List<String> ids(JsonNode test) {
		return test.get("document").get("steps").valueStream().map(s -> s.get("id").asString()).toList();
	}

	private JsonNode withoutIds(JsonNode steps) {
		JsonNode copy = steps.deepCopy();
		copy.forEach(s -> ((tools.jackson.databind.node.ObjectNode) s).remove("id"));
		return copy;
	}

	private long stepNodes() {
		return count("MATCH (s:Step) RETURN count(s) AS n");
	}

	private long count(String query) {
		return driver.executableQuery(query).execute().records().get(0).get("n").asLong();
	}

}
