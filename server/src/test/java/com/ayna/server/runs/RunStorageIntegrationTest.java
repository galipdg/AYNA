package com.ayna.server.runs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.ObjectMapper;

/**
 * Screenshots, the idle timeout and retention (#51) against a real Neo4j started by
 * Testcontainers (needs Docker) and a temporary screenshot folder.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class RunStorageIntegrationTest {

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
	RunHousekeeping housekeeping;

	@Autowired
	StepSchema stepSchema;

	@Value("${ayna.screenshots.dir}")
	Path folder;

	String appId;

	String versionId;

	String testId;

	List<String> stepIds;

	@BeforeEach
	void setUp() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		appId = id(mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "Müşteri Kayıt", "technology", "PySide6")))));
		versionId = id(mvc.perform(post("/api/apps/{id}/versions", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", "1.0.0")))));
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: 'login.loginButton'})""")
			.withParameters(Map.of("appId", appId))
			.execute();
		testId = id(mvc.perform(post("/api/apps/{id}/tests", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "Giriş")))));
		Map<String, Object> click = Map.of("keyword", "Click", "target", "login.loginButton");
		String steps = mvc
			.perform(put("/api/tests/{id}/steps", testId).contentType(MediaType.APPLICATION_JSON)
				.content(mapper.writeValueAsString(
						Map.of("version", stepSchema.version(), "steps", List.of(click, click, click)))))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();
		stepIds = JsonPath.read(steps, "$.document.steps[*].id");
	}

	// --- Screenshots -------------------------------------------------------------------------

	@Test
	void storesAScreenshotAsAFileAndServesItBack() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		byte[] png = png("first");

		String stepResultId = JsonPath.read(upload(runId, 0, png).andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString(), "$.stepResultId");

		assertThat(Files.readAllBytes(folder.resolve(runId).resolve("0.png"))).isEqualTo(png);
		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 0))
			.andExpect(status().isOk())
			.andExpect(header().string("Content-Type", MediaType.IMAGE_PNG_VALUE))
			.andExpect(content().bytes(png));
		mvc.perform(get("/api/runs/{id}", runId))
			.andExpect(jsonPath("$.results[0].id").value(stepResultId))
			.andExpect(jsonPath("$.results[0].screenshotUrl").value("/api/runs/" + runId + "/results/0/screenshot"));
		assertThat(stepResultProperty(runId, 0, "screenshotPath")).isEqualTo(runId + "/0.png");
	}

	@Test
	void aResultWithoutAScreenshotSaysSo() throws Exception {
		String runId = startRun();
		passed(runId, 0);

		mvc.perform(get("/api/runs/{id}", runId)).andExpect(jsonPath("$.results[0].screenshotUrl").value(nullValue()));
		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 0))
			.andExpect(status().isNotFound())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value(containsString("no screenshot")));
		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 1)).andExpect(status().isNotFound());
		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", UNKNOWN, 0)).andExpect(status().isNotFound());
	}

	@Test
	void theSameImageAgainIsARepeatAndAnotherImageAConflict() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		upload(runId, 0, png("first")).andExpect(status().isCreated());

		upload(runId, 0, png("first")).andExpect(status().isOk());
		upload(runId, 0, png("second")).andExpect(status().isConflict())
			.andExpect(jsonPath("$.detail").value(containsString("different screenshot")));

		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 0)).andExpect(content().bytes(png("first")));
	}

	@Test
	void aRepeatWritesTheFileAgainWhenItIsMissing() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		upload(runId, 0, png("first")).andExpect(status().isCreated());
		Files.delete(folder.resolve(runId).resolve("0.png"));

		upload(runId, 0, png("first")).andExpect(status().isOk());

		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 0)).andExpect(content().bytes(png("first")));
	}

	@Test
	void theResultComesFirst() throws Exception {
		String runId = startRun();

		upload(runId, 0, png("first")).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.detail").value(containsString("send the result first")));
		upload(UNKNOWN, 0, png("first")).andExpect(status().isNotFound());
		assertThat(Files.exists(folder.resolve(runId))).isFalse();
	}

	@Test
	void aFinishedRunStillTakesTheScreenshotOfAStoredResult() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		finish(runId, "aborted");

		upload(runId, 0, png("late")).andExpect(status().isCreated());
	}

	@Test
	void refusesWhatIsNotAPng() throws Exception {
		String runId = startRun();
		passed(runId, 0);

		upload(runId, 0, "GIF89a not a png".getBytes(StandardCharsets.US_ASCII)).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.detail").value(containsString("PNG")));
		upload(runId, 0, new byte[0]).andExpect(status().isBadRequest());
		mvc.perform(put("/api/runs/{id}/results/{i}/screenshot", runId, 0).contentType(MediaType.IMAGE_JPEG)
			.content(png("first"))).andExpect(status().isUnsupportedMediaType());
		assertThat(stepResultProperty(runId, 0, "screenshotPath")).isNull();
	}

	@Test
	void refusesAScreenshotOverTheLimit() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		byte[] big = Arrays.copyOf(png("big"), 8 * 1024 * 1024 + 1);

		upload(runId, 0, big).andExpect(status().isContentTooLarge())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
		assertThat(stepResultProperty(runId, 0, "screenshotPath")).isNull();
	}

	@Test
	void deletingATestDeletesItsScreenshots() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		upload(runId, 0, png("first")).andExpect(status().isCreated());

		mvc.perform(delete("/api/tests/{id}", testId)).andExpect(status().isNoContent());

		assertThat(Files.exists(folder.resolve(runId))).isFalse();
	}

	@Test
	void removesScreenshotFoldersWhoseRunIsGone() throws Exception {
		String kept = startRun();
		passed(kept, 0);
		upload(kept, 0, png("kept")).andExpect(status().isCreated());
		Path orphan = Files.createDirectories(folder.resolve(UUID.randomUUID().toString()));
		Files.write(orphan.resolve("0.png"), png("orphan"));
		Path notARun = Files.createDirectories(folder.resolve("not-a-run"));

		housekeeping.removeOrphanScreenshots();

		assertThat(Files.exists(orphan)).isFalse();
		assertThat(Files.exists(notARun)).isTrue();
		assertThat(Files.exists(folder.resolve(kept).resolve("0.png"))).isTrue();
	}

	// --- Idle timeout ------------------------------------------------------------------------

	@Test
	void aRunWithNoWriteForTheIdleTimeoutEndsAsAborted() throws Exception {
		String idle = startRun();
		passed(idle, 0);
		String active = startRun();
		lastActivity(idle, "PT2H");
		lastActivity(active, "PT2H");
		passed(active, 0);

		List<RunDtos.RunSummary> aborted = service.abortIdleRuns(Duration.ofMinutes(60));

		assertThat(aborted).extracting(RunDtos.RunSummary::id).containsExactly(idle);
		mvc.perform(get("/api/runs/{id}", idle))
			.andExpect(jsonPath("$.status").value("aborted"))
			.andExpect(jsonPath("$.finishedAt").isString())
			.andExpect(jsonPath("$.durationMs").isNumber());
		mvc.perform(get("/api/runs/{id}", active)).andExpect(jsonPath("$.status").value("running"));
		passed(idle, 1).andExpect(status().isConflict());
	}

	@Test
	void anEndedRunIsNotAbortedLater() throws Exception {
		String runId = startRun();
		passed(runId, 0);
		finish(runId, "aborted");
		lastActivity(runId, "PT2H");

		assertThat(service.abortIdleRuns(Duration.ofMinutes(60))).isEmpty();
	}

	// --- Retention ---------------------------------------------------------------------------

	@Test
	void retentionKeepsTheNewestRunsAndNeverARunningOne() throws Exception {
		List<String> runs = new ArrayList<>();
		for (int i = 0; i < 5; i++) {
			String runId = startRun();
			passed(runId, 0);
			upload(runId, 0, png("run " + i)).andExpect(status().isCreated());
			runs.add(runId);
		}
		for (int i = 1; i < 5; i++) {
			finish(runs.get(i), "aborted");
		}
		// runs.get(0) is the oldest and still running.
		for (int i = 0; i < 5; i++) {
			startedAt(runs.get(i), "2026-11-0" + (i + 1) + "T10:00:00Z");
		}

		List<String> deleted = service.deleteOldRuns(2);

		assertThat(deleted).containsExactlyInAnyOrder(runs.get(1), runs.get(2));
		assertThat(remainingRuns()).containsExactlyInAnyOrder(runs.get(0), runs.get(3), runs.get(4));
		assertThat(Files.exists(folder.resolve(runs.get(1)))).isFalse();
		assertThat(Files.exists(folder.resolve(runs.get(2)))).isFalse();
		assertThat(Files.exists(folder.resolve(runs.get(4)).resolve("0.png"))).isTrue();
		assertThat(count("MATCH (sr:StepResult) WHERE sr.runId IN $ids RETURN count(sr) AS n",
				Map.of("ids", List.of(runs.get(1), runs.get(2))))).isZero();
		mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runs.get(1), 0)).andExpect(status().isNotFound());
	}

	@Test
	void retentionDeletesInBatches() throws Exception {
		int runs = RunService.RETENTION_BATCH * 2 + 3;
		driver.executableQuery("""
				MATCH (t:TestCase {id: $testId}), (v:AppVersion {id: $versionId})
				UNWIND range(1, $runs) AS i
				CREATE (r:Run {id: randomUUID(), status: 'aborted', stepCount: 3, document: '{}', startedBy: 'x',
				  startedAt: datetime() - duration({minutes: i})})
				CREATE (r)-[:OF]->(t)
				CREATE (r)-[:ON_VERSION]->(v)""")
			.withParameters(Map.of("testId", testId, "versionId", versionId, "runs", runs))
			.execute();

		assertThat(service.deleteOldRuns(1)).hasSize(runs - 1);
		assertThat(remainingRuns()).hasSize(1);
	}

	/** Acceptance criterion of #51 and NFR-28: 100 consecutive runs, every screenshot retrievable. */
	@Test
	void aHundredConsecutiveRunsKeepEveryScreenshotRetrievable() throws Exception {
		List<String> runs = new ArrayList<>();
		for (int run = 0; run < 100; run++) {
			String runId = startRun();
			for (int step = 0; step < 3; step++) {
				passed(runId, step).andExpect(status().isCreated());
				upload(runId, step, png(run + "/" + step)).andExpect(status().isCreated());
			}
			finish(runId, "passed").andExpect(status().isOk());
			runs.add(runId);
		}

		for (int run = 0; run < 100; run++) {
			for (int step = 0; step < 3; step++) {
				mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runs.get(run), step))
					.andExpect(status().isOk())
					.andExpect(content().bytes(png(run + "/" + step)));
			}
		}

		service.deleteOldRuns(50);
		List<String> remaining = remainingRuns();
		assertThat(remaining).containsExactlyInAnyOrderElementsOf(runs.subList(50, 100));
		for (String runId : runs.subList(0, 50)) {
			assertThat(Files.exists(folder.resolve(runId))).isFalse();
		}
		for (String runId : remaining) {
			mvc.perform(get("/api/runs/{id}/results/{i}/screenshot", runId, 2)).andExpect(status().isOk());
		}
	}

	// --- Helpers -----------------------------------------------------------------------------

	/** A small valid-looking PNG: the signature, then text that makes each image different. */
	private static byte[] png(String text) {
		byte[] signature = { (byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n' };
		byte[] body = text.getBytes(StandardCharsets.UTF_8);
		byte[] png = Arrays.copyOf(signature, signature.length + body.length);
		System.arraycopy(body, 0, png, signature.length, body.length);
		return png;
	}

	private String startRun() throws Exception {
		return id(mvc.perform(post("/api/runs").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("testId", testId, "appVersionId", versionId)))));
	}

	private ResultActions passed(String runId, int index) throws Exception {
		Map<String, Object> body = new HashMap<>();
		body.put("runId", runId);
		body.put("stepIndex", index);
		body.put("stepId", stepIds.get(index));
		body.put("status", "passed");
		return mvc.perform(put("/api/runs/{id}/results/{index}", runId, index).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(body)));
	}

	private ResultActions upload(String runId, int index, byte[] png) throws Exception {
		return mvc.perform(
				put("/api/runs/{id}/results/{i}/screenshot", runId, index).contentType(MediaType.IMAGE_PNG).content(png));
	}

	private ResultActions finish(String runId, String status) throws Exception {
		return mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("status", status))));
	}

	private void lastActivity(String runId, String ago) {
		driver.executableQuery("MATCH (r:Run {id: $id}) SET r.lastActivityAt = datetime() - duration($ago)")
			.withParameters(Map.of("id", runId, "ago", ago))
			.execute();
	}

	private void startedAt(String runId, String at) {
		driver.executableQuery("MATCH (r:Run {id: $id}) SET r.startedAt = datetime($at)")
			.withParameters(Map.of("id", runId, "at", at))
			.execute();
	}

	private List<String> remainingRuns() {
		return driver.executableQuery("MATCH (r:Run) RETURN r.id AS id")
			.execute()
			.records()
			.stream()
			.map(r -> r.get("id").asString())
			.toList();
	}

	private String stepResultProperty(String runId, int index, String property) {
		return driver.executableQuery("MATCH (sr:StepResult {runId: $id, stepIndex: $index}) RETURN sr[$property] AS v")
			.withParameters(Map.of("id", runId, "index", index, "property", property))
			.execute()
			.records()
			.get(0)
			.get("v")
			.asString(null);
	}

	private long count(String query, Map<String, Object> params) {
		return driver.executableQuery(query).withParameters(params).execute().records().get(0).get("n").asLong();
	}

	private static String id(ResultActions created) throws Exception {
		return JsonPath.read(created.andReturn().getResponse().getContentAsString(), "$.id");
	}

}
