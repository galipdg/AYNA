package com.ayna.server.runs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.stream.IntStream;

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
import com.ayna.server.runs.RunService.StoredResult;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Runs and step results against a real Neo4j started by Testcontainers (needs Docker). */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class RunIntegrationTest {

	static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

	static final String UNKNOWN = "00000000-0000-0000-0000-000000000000";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	RunService service;

	@Autowired
	StepSchema stepSchema;

	String appId;

	String versionId;

	String testId;

	List<String> stepIds;

	/** Domain nodes only: the migration tool's `__`-prefixed nodes must stay. */
	@BeforeEach
	void setUp() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		appId = createApp("Müşteri Kayıt");
		versionId = createVersion(appId, "1.0.0");
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: 'login.loginButton'})""")
			.withParameters(Map.of("appId", appId))
			.execute();
		testId = createTest("Giriş");
		stepIds = replaceSteps(testId, click(), click(), click());
	}

	@Test
	void startsARunWithACopyOfTheSteps() throws Exception {
		createRun(testId, versionId).andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(matchesPattern(UUID_PATTERN)))
			.andExpect(header().string("Location", matchesPattern("/api/runs/" + UUID_PATTERN)))
			.andExpect(jsonPath("$.testId").value(testId))
			.andExpect(jsonPath("$.appVersionId").value(versionId))
			.andExpect(jsonPath("$.status").value("running"))
			.andExpect(jsonPath("$.stepCount").value(3))
			.andExpect(jsonPath("$.startedBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.startedAt").isString())
			.andExpect(jsonPath("$.finishedAt").value(nullValue()))
			.andExpect(jsonPath("$.durationMs").value(nullValue()))
			.andExpect(jsonPath("$.document.steps[*].id").value(contains(stepIds.toArray())))
			.andExpect(jsonPath("$.results", hasSize(0)));
	}

	@Test
	void linksTheRunToItsTestAndVersion() throws Exception {
		String runId = id(createRun(testId, versionId));

		assertThat(count("MATCH (:Run {id: $id})-[:OF]->(:TestCase {id: $testId}) RETURN count(*) AS n",
				Map.of("id", runId, "testId", testId))).isEqualTo(1);
		assertThat(count("MATCH (:Run {id: $id})-[:ON_VERSION]->(:AppVersion {id: $versionId}) RETURN count(*) AS n",
				Map.of("id", runId, "versionId", versionId))).isEqualTo(1);
	}

	@Test
	void editingTheTestLaterDoesNotChangeTheRunsCopy() throws Exception {
		String runId = id(createRun(testId, versionId));
		replaceSteps(testId, click());

		mvc.perform(get("/api/runs/{id}", runId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.stepCount").value(3))
			.andExpect(jsonPath("$.document.steps[*].id").value(contains(stepIds.toArray())));
	}

	@Test
	void startingARunChecksItsTestAndVersion() throws Exception {
		createRun(UNKNOWN, versionId).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.detail").value(containsString(UNKNOWN)));
		createRun(testId, UNKNOWN).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.detail").value(containsString(UNKNOWN)));
		createRun(testId, createVersion(createApp("Notepad"), "2.0")).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.appVersionId"));
		createRun(createTest("Boş"), versionId).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.detail").value(containsString("no steps")));
		mvc.perform(post("/api/runs").contentType(MediaType.APPLICATION_JSON).content("{\"testId\":\" \"}"))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.testId"));
	}

	@Test
	void storesResultsInStepOrder() throws Exception {
		String runId = id(createRun(testId, versionId));

		writeResult(runId, 1, result(runId, 1, "passed")).andExpect(status().isCreated())
			.andExpect(jsonPath("$.stepResultId").value(matchesPattern(UUID_PATTERN)));
		Map<String, Object> failed = result(runId, 0, "failed");
		failed.put("durationMs", 120);
		failed.put("message", "Öge 500 ms sonra bulunamadı");
		writeResult(runId, 0, failed).andExpect(status().isCreated());

		mvc.perform(get("/api/runs/{id}", runId))
			.andExpect(jsonPath("$.results[*].stepIndex").value(contains(0, 1)))
			.andExpect(jsonPath("$.results[0].stepId").value(stepIds.get(0)))
			.andExpect(jsonPath("$.results[0].status").value("failed"))
			.andExpect(jsonPath("$.results[0].durationMs").value(120))
			.andExpect(jsonPath("$.results[0].message").value("Öge 500 ms sonra bulunamadı"))
			.andExpect(jsonPath("$.results[0].receivedAt").isString())
			.andExpect(jsonPath("$.results[1].status").value("passed"));
		assertThat(count("MATCH (:StepResult {runId: $id, stepIndex: 1})-[:FOR]->(:Step {id: $stepId}) RETURN count(*) AS n",
				Map.of("id", runId, "stepId", stepIds.get(1)))).isEqualTo(1);
	}

	@Test
	void anIdenticalRepeatChangesNothingWhateverItsKeyOrder() throws Exception {
		String runId = id(createRun(testId, versionId));
		String first = String.format(
				"{\"runId\":\"%s\",\"stepIndex\":0,\"stepId\":\"%s\",\"status\":\"passed\",\"extra\":{\"a\":1,\"b\":2}}",
				runId, stepIds.get(0));
		String reordered = String.format(
				"{\"extra\":{\"b\":2,\"a\":1},\"status\":\"passed\",\"stepId\":\"%s\",\"stepIndex\":0,\"runId\":\"%s\"}",
				stepIds.get(0), runId);

		String stored = writeRaw(runId, 0, first).andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		writeRaw(runId, 0, reordered).andExpect(status().isOk()).andExpect(content().json(stored));

		assertThat(resultCount(runId)).isEqualTo(1);
	}

	@Test
	void anotherBodyForTheSameStepIsAConflict() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed")).andExpect(status().isCreated());

		writeResult(runId, 0, result(runId, 0, "failed")).andExpect(status().isConflict())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value(containsString(runId)));

		mvc.perform(get("/api/runs/{id}", runId)).andExpect(jsonPath("$.results[0].status").value("passed"));
	}

	@Test
	void overlappingRetriesStoreOneResult() throws Exception {
		String runId = id(createRun(testId, versionId));
		JsonNode body = mapper.valueToTree(result(runId, 0, "passed"));
		CountDownLatch start = new CountDownLatch(1);

		List<CompletableFuture<StoredResult>> writes = IntStream.range(0, 8)
			.mapToObj(i -> CompletableFuture.supplyAsync(() -> {
				try {
					start.await();
				}
				catch (InterruptedException ex) {
					throw new IllegalStateException(ex);
				}
				return service.writeResult(runId, 0, body);
			}))
			.toList();
		start.countDown();

		List<StoredResult> results = writes.stream().map(CompletableFuture::join).toList();
		assertThat(results).filteredOn(StoredResult::created).hasSize(1);
		assertThat(results).extracting(StoredResult::id).containsOnly(results.get(0).id());
		assertThat(resultCount(runId)).isEqualTo(1);
	}

	@Test
	void membersTheServerDoesNotReadAreKept() throws Exception {
		String runId = id(createRun(testId, versionId));
		Map<String, Object> body = result(runId, 0, "passed");
		body.put("screenshotAt", "2026-11-05T10:00:00Z");
		writeResult(runId, 0, body).andExpect(status().isCreated());

		String stored = driver.executableQuery("MATCH (r:StepResult {runId: $id}) RETURN r.body AS body")
			.withParameters(Map.of("id", runId))
			.execute()
			.records()
			.get(0)
			.get("body")
			.asString();
		assertThat(mapper.readTree(stored).path("screenshotAt").asString()).isEqualTo("2026-11-05T10:00:00Z");
	}

	@Test
	void refusesAnInvalidResultAndNamesTheField() throws Exception {
		String runId = id(createRun(testId, versionId));
		record Bad(int index, Map<String, Object> changes, String path) {
		}
		List<Bad> cases = new ArrayList<>(List.of(new Bad(0, Map.of("runId", UNKNOWN), "$.runId"),
				new Bad(0, Map.of("stepIndex", 1), "$.stepIndex"), new Bad(0, Map.of("stepIndex", "0"), "$.stepIndex"),
				new Bad(3, Map.of("stepIndex", 3), "$.stepIndex"), new Bad(-1, Map.of("stepIndex", -1), "$.stepIndex"),
				new Bad(0, Map.of("stepId", stepIds.get(1)), "$.stepId"), new Bad(0, Map.of("stepId", 7), "$.stepId"),
				new Bad(0, Map.of("status", "skipped"), "$.status"),
				new Bad(0, Map.of("status", "repairProposed"), "$.status"),
				new Bad(0, Map.of("durationMs", -1), "$.durationMs"), new Bad(0, Map.of("durationMs", 1.5), "$.durationMs"),
				new Bad(0, Map.of("message", 5), "$.message"), new Bad(0, Map.of("runId", Map.of()), "$.runId"),
				new Bad(0, Map.of("stepIndex", List.of()), "$.stepIndex"), new Bad(0, Map.of("status", List.of()), "$.status"),
				new Bad(0, Map.of("status", Map.of()), "$.status"), new Bad(0, Map.of("stepId", Map.of()), "$.stepId")));
		for (Bad bad : cases) {
			Map<String, Object> body = result(runId, bad.index(), "passed");
			body.putAll(bad.changes());
			writeResult(runId, bad.index(), body).andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.errors[0].path").value(bad.path()));
		}
		writeRaw(runId, 0, "[1]").andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors[0].path").value("$"));
		assertThat(resultCount(runId)).isZero();
	}

	@Test
	void aStepWithoutAnIdCanStillBeRecorded() throws Exception {
		String runId = id(createRun(testId, versionId));
		Map<String, Object> body = result(runId, 0, "passed");
		body.put("stepId", null);

		writeResult(runId, 0, body).andExpect(status().isCreated());

		mvc.perform(get("/api/runs/{id}", runId)).andExpect(jsonPath("$.results[0].stepId").value(nullValue()));
	}

	@Test
	void aResultForADeletedStepIsStoredWithoutTheLink() throws Exception {
		String runId = id(createRun(testId, versionId));
		replaceSteps(testId, click());

		writeResult(runId, 2, result(runId, 2, "passed")).andExpect(status().isCreated());

		assertThat(count("MATCH (:StepResult {runId: $id})-[:FOR]->() RETURN count(*) AS n", Map.of("id", runId))).isZero();
	}

	@Test
	void anUnknownRunIsNotFound() throws Exception {
		writeResult(UNKNOWN, 0, result(UNKNOWN, 0, "passed")).andExpect(status().isNotFound());
		finish(UNKNOWN, "aborted").andExpect(status().isNotFound());
		mvc.perform(get("/api/runs/{id}", UNKNOWN)).andExpect(status().isNotFound());
	}

	@Test
	void aRunPassesOnlyWhenEveryStepPassed() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));
		writeResult(runId, 1, result(runId, 1, "passed"));

		finish(runId, "passed").andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value(containsString("2 of 3")));

		writeResult(runId, 2, result(runId, 2, "passed"));
		String body = finish(runId, "passed").andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("passed"))
			.andReturn()
			.getResponse()
			.getContentAsString();

		Instant startedAt = Instant.parse(JsonPath.read(body, "$.startedAt"));
		Instant finishedAt = Instant.parse(JsonPath.read(body, "$.finishedAt"));
		Number duration = JsonPath.read(body, "$.durationMs");
		assertThat(duration.longValue()).isEqualTo(Duration.between(startedAt, finishedAt).toMillis());
	}

	@Test
	void aRunWithAFailedStepCannotPass() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));
		writeResult(runId, 1, result(runId, 1, "failed"));
		writeResult(runId, 2, result(runId, 2, "notRun"));

		finish(runId, "passed").andExpect(status().isConflict());
		finish(runId, "failed").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("failed"));
	}

	@Test
	void aRunCannotFailWithoutAFailedStep() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));

		finish(runId, "failed").andExpect(status().isConflict());
	}

	@Test
	void aRunCanBeAbortedWithGaps() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));

		finish(runId, "aborted").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("aborted"));
	}

	@Test
	void finishingTwice() throws Exception {
		String runId = id(createRun(testId, versionId));

		String first = finish(runId, "aborted").andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
		finish(runId, "aborted").andExpect(status().isOk()).andExpect(content().json(first));
		finish(runId, "failed").andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value(containsString("aborted")));
	}

	@Test
	void aFinishStatusThatIsNotTextIsRefused() throws Exception {
		String runId = id(createRun(testId, versionId));

		mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"status\":{\"a\":1}}")).andExpect(status().isBadRequest());
	}

	@Test
	void anUnknownFinishStatusIsRefused() throws Exception {
		String runId = id(createRun(testId, versionId));

		finish(runId, "running").andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[0].path").value("$.status"));
		mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON).content("{}"))
			.andExpect(status().isBadRequest());
	}

	@Test
	void aFinishedRunTakesNoNewResultButAcceptsARepeat() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));
		finish(runId, "aborted");

		writeResult(runId, 1, result(runId, 1, "passed")).andExpect(status().isConflict());
		writeResult(runId, 0, result(runId, 0, "passed")).andExpect(status().isOk());
	}

	@Test
	void listsATestsRunsNewestFirst() throws Exception {
		String first = id(createRun(testId, versionId));
		finish(first, "aborted");
		String second = id(createRun(testId, versionId));
		String other = createTest("Başka");
		replaceSteps(other, click());
		id(createRun(other, versionId));

		mvc.perform(get("/api/tests/{id}/runs", testId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[*].id").value(contains(second, first)))
			.andExpect(jsonPath("$[0].document").doesNotExist())
			.andExpect(jsonPath("$[0].results").doesNotExist());
		mvc.perform(get("/api/tests/{id}/runs", testId).param("status", "running"))
			.andExpect(jsonPath("$[*].id").value(contains(second)));
	}

	@Test
	void theRunListStopsAtTwenty() throws Exception {
		for (int i = 0; i < RunService.HISTORY_LIMIT + 1; i++) {
			createRun(testId, versionId).andExpect(status().isCreated());
		}

		mvc.perform(get("/api/tests/{id}/runs", testId)).andExpect(jsonPath("$", hasSize(RunService.HISTORY_LIMIT)));
	}

	@Test
	void theRunListChecksItsArguments() throws Exception {
		mvc.perform(get("/api/tests/{id}/runs", UNKNOWN)).andExpect(status().isNotFound());
		mvc.perform(get("/api/tests/{id}/runs", testId).param("status", "paused")).andExpect(status().isBadRequest());
	}

	@Test
	void listsAnApplicationsRunsAcrossItsTestsNewestFirst() throws Exception {
		String first = id(createRun(testId, versionId));
		finish(first, "aborted");
		String other = createTest("Başka");
		replaceSteps(other, click());
		String second = id(createRun(other, versionId));
		String otherApp = createApp("Başka Uygulama");
		String otherVersion = createVersion(otherApp, "1.0.0");
		String elsewhere = id(mvc.perform(post("/api/apps/{id}/tests", otherApp).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "Giriş")))));
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: 'login.loginButton'})""")
			.withParameters(Map.of("appId", otherApp))
			.execute();
		replaceSteps(elsewhere, click());
		createRun(elsewhere, otherVersion).andExpect(status().isCreated());

		mvc.perform(get("/api/apps/{id}/runs", appId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[*].id").value(contains(second, first)))
			.andExpect(jsonPath("$[0].testId").value(other))
			.andExpect(jsonPath("$[1].startedBy.id").isString())
			.andExpect(jsonPath("$[0].document").doesNotExist());
		mvc.perform(get("/api/apps/{id}/runs", appId).param("testId", testId))
			.andExpect(jsonPath("$[*].id").value(contains(first)));
		mvc.perform(get("/api/apps/{id}/runs", appId).param("status", "running"))
			.andExpect(jsonPath("$[*].id").value(contains(second)));
		mvc.perform(get("/api/apps/{id}/runs", appId).param("testId", testId).param("status", "running"))
			.andExpect(jsonPath("$", hasSize(0)));
	}

	@Test
	void theApplicationRunListStopsAtItsLimit() throws Exception {
		driver.executableQuery("""
				MATCH (t:TestCase {id: $testId}), (v:AppVersion {id: $versionId})
				UNWIND range(1, $n) AS i
				CREATE (r:Run {id: randomUUID(), status: 'passed', stepCount: 3, document: '{}', startedBy: 'nobody',
				  startedAt: datetime() - duration({seconds: i}), lastActivityAt: datetime()})
				CREATE (r)-[:OF]->(t)
				CREATE (r)-[:ON_VERSION]->(v)""")
			.withParameters(
					Map.of("testId", testId, "versionId", versionId, "n", RunService.APP_HISTORY_LIMIT + 1))
			.execute();

		mvc.perform(get("/api/apps/{id}/runs", appId))
			.andExpect(jsonPath("$", hasSize(RunService.APP_HISTORY_LIMIT)));
	}

	@Test
	void theApplicationRunListChecksItsArguments() throws Exception {
		String otherApp = createApp("Başka Uygulama");

		mvc.perform(get("/api/apps/{id}/runs", UNKNOWN)).andExpect(status().isNotFound());
		mvc.perform(get("/api/apps/{id}/runs", otherApp).param("testId", testId))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.detail").value("Test not found in this application: " + testId));
		mvc.perform(get("/api/apps/{id}/runs", appId).param("status", "paused")).andExpect(status().isBadRequest());
	}

	@Test
	void deletingATestDeletesItsRunsAndResults() throws Exception {
		String runId = id(createRun(testId, versionId));
		writeResult(runId, 0, result(runId, 0, "passed"));

		mvc.perform(delete("/api/tests/{id}", testId)).andExpect(status().isNoContent());

		assertThat(count("MATCH (r:Run) RETURN count(r) AS n", Map.of())).isZero();
		assertThat(count("MATCH (r:StepResult) RETURN count(r) AS n", Map.of())).isZero();
		writeResult(runId, 1, result(runId, 1, "passed")).andExpect(status().isNotFound());
	}

	private Map<String, Object> result(String runId, int index, String status) {
		Map<String, Object> body = new HashMap<>();
		body.put("runId", runId);
		body.put("stepIndex", index);
		body.put("stepId", index >= 0 && index < stepIds.size() ? stepIds.get(index) : UNKNOWN);
		body.put("status", status);
		return body;
	}

	private long resultCount(String runId) {
		return count("MATCH (r:StepResult {runId: $id}) RETURN count(r) AS n", Map.of("id", runId));
	}

	private long count(String query, Map<String, Object> params) {
		return driver.executableQuery(query).withParameters(params).execute().records().get(0).get("n").asLong();
	}

	private ResultActions createRun(String test, String version) throws Exception {
		return mvc.perform(post("/api/runs").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("testId", test, "appVersionId", version))));
	}

	private ResultActions writeResult(String runId, int index, Map<String, Object> body) throws Exception {
		return writeRaw(runId, index, mapper.writeValueAsString(body));
	}

	private ResultActions writeRaw(String runId, int index, String body) throws Exception {
		return mvc.perform(put("/api/runs/{id}/results/{index}", runId, index).contentType(MediaType.APPLICATION_JSON)
			.content(body));
	}

	private ResultActions finish(String runId, String status) throws Exception {
		return mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("status", status))));
	}

	private String createApp(String name) throws Exception {
		return id(mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name, "technology", "PySide6")))));
	}

	private String createVersion(String app, String version) throws Exception {
		return id(mvc.perform(post("/api/apps/{id}/versions", app).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", version)))));
	}

	private String createTest(String name) throws Exception {
		return id(mvc.perform(post("/api/apps/{id}/tests", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name)))));
	}

	@SafeVarargs
	private List<String> replaceSteps(String test, Map<String, Object>... steps) throws Exception {
		String body = mvc
			.perform(put("/api/tests/{id}/steps", test).contentType(MediaType.APPLICATION_JSON)
				.content(mapper.writeValueAsString(Map.of("version", stepSchema.version(), "steps", List.of(steps)))))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();
		return JsonPath.read(body, "$.document.steps[*].id");
	}

	private static Map<String, Object> click() {
		return Map.of("keyword", "Click", "target", "login.loginButton");
	}

	private static String id(ResultActions created) throws Exception {
		return JsonPath.read(created.andReturn().getResponse().getContentAsString(), "$.id");
	}

}
