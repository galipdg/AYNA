package com.ayna.server.runs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

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
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.ObjectMapper;

/**
 * The HTML run report (#59) against a real Neo4j started by Testcontainers (needs Docker) and a
 * temporary screenshot folder.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class RunReportIntegrationTest {

	static final String UNKNOWN = "00000000-0000-0000-0000-000000000000";

	/** A measured 1920 × 1080 full-screen PNG is 222 KB (ADR run-screenshots-and-retention). */
	static final int SCREENSHOT_BYTES = 222 * 1024;

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	StepSchema stepSchema;

	@Value("${ayna.screenshots.dir}")
	Path folder;

	String appId;

	String versionId;

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
	}

	@Test
	void containsEveryStepWithItsScreenshot() throws Exception {
		SavedTest test = test("Giriş", 3);
		String runId = startRun(test.id());
		List<byte[]> images = new ArrayList<>();
		for (int i = 0; i < 3; i++) {
			result(runId, i, test.stepIds().get(i), "passed").andExpect(status().isCreated());
			images.add(png(i, 64));
			upload(runId, i, images.get(i)).andExpect(status().isCreated());
		}
		finish(runId, "passed");

		MvcResult started = mvc.perform(get("/api/runs/{id}/report.html", runId))
			.andExpect(request().asyncStarted())
			.andReturn();
		String html = mvc.perform(asyncDispatch(started))
			.andExpect(status().isOk())
			.andExpect(header().string("Content-Type", "text/html;charset=UTF-8"))
			.andExpect(header().string("Cache-Control", "no-store"))
			.andExpect(header().string("Content-Security-Policy", RunReport.CONTENT_SECURITY_POLICY))
			.andExpect(header().string("Content-Disposition", "inline; filename=\"ayna-run-" + runId + ".html\""))
			.andReturn()
			.getResponse()
			.getContentAsString(StandardCharsets.UTF_8);

		assertThat(html).contains("<title>Run report · Giriş</title>")
			.contains("Müşteri Kayıt 1.0.0")
			.contains("<span class=\"badge passed\">Passed</span></h1>")
			.doesNotContain("No screenshot for this step");
		for (int i = 0; i < 3; i++) {
			assertThat(html).contains("<tbody id=\"step-" + (i + 1) + "\" class=\"passed\">")
				.contains("src=\"data:image/png;base64," + Base64.getEncoder().encodeToString(images.get(i)) + "\"");
		}
	}

	@Test
	void everyRunHasOneWhileRunningAndAfterAnAbort() throws Exception {
		SavedTest test = test("Giriş", 3);
		String runId = startRun(test.id());
		result(runId, 0, test.stepIds().get(0), "passed");

		String running = report(runId, "");
		assertThat(running).contains("Running").contains("2 no result").contains("No screenshot for this step");

		finish(runId, "aborted");
		assertThat(report(runId, "")).contains("<span class=\"badge aborted\">Aborted</span>");
	}

	@Test
	void aFailedStepShowsItsMessageAndIsLinkedFromTheTop() throws Exception {
		SavedTest test = test("Giriş", 3);
		String runId = startRun(test.id());
		result(runId, 0, test.stepIds().get(0), "passed");
		Map<String, Object> failed = body(runId, 1, test.stepIds().get(1), "failed");
		failed.put("message", "Element login.loginButton not found within 20000 ms");
		failed.put("durationMs", 20012);
		mvc.perform(put("/api/runs/{id}/results/{index}", runId, 1).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(failed))).andExpect(status().isCreated());
		result(runId, 2, test.stepIds().get(2), "notRun");
		finish(runId, "failed");

		assertThat(report(runId, "")).contains("<a href=\"#step-2\">First failed step: 2</a>")
			.contains("Element login.loginButton not found within 20000 ms")
			.contains("20.0 s")
			.contains("<tbody id=\"step-3\" class=\"notRun\">");
	}

	@Test
	void aScreenshotWhoseFileHasGoneIsAStepWithoutOne() throws Exception {
		SavedTest test = test("Giriş", 1);
		String runId = startRun(test.id());
		result(runId, 0, test.stepIds().get(0), "passed");
		upload(runId, 0, png(0, 64)).andExpect(status().isCreated());
		Files.delete(folder.resolve(runId).resolve("0.png"));

		assertThat(report(runId, "")).contains("No screenshot for this step").doesNotContain("data:image/png");
	}

	@Test
	void speaksTurkishWhenAskedAndRefusesOtherLanguages() throws Exception {
		SavedTest test = test("Giriş", 1);
		String runId = startRun(test.id());

		assertThat(report(runId, "tr")).contains("<html lang=\"tr\">").contains("Çalıştırma raporu").contains("Tıkla");
		mvc.perform(get("/api/runs/{id}/report.html", runId).param("lang", "de"))
			.andExpect(status().isBadRequest())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
	}

	@Test
	void anUnknownRunIsA404WithAProblemBody() throws Exception {
		mvc.perform(get("/api/runs/{id}/report.html", UNKNOWN))
			.andExpect(status().isNotFound())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value("Run not found: " + UNKNOWN));
	}

	/** NFR-09: the report of a 50-step run within 5 s, here with a full-screen-sized PNG per step. */
	@Test
	void aFiftyStepRunIsReportedWithinFiveSeconds() throws Exception {
		SavedTest test = test("Uzun", 50);
		String runId = startRun(test.id());
		for (int i = 0; i < 50; i++) {
			result(runId, i, test.stepIds().get(i), "passed");
			upload(runId, i, png(i, SCREENSHOT_BYTES)).andExpect(status().isCreated());
		}
		finish(runId, "passed");
		report(runId, ""); // warm-up: the first request of a context pays for class loading

		long started = System.nanoTime();
		String html = report(runId, "");
		long elapsedMs = (System.nanoTime() - started) / 1_000_000;

		assertThat(elapsedMs).isLessThan(5000);
		assertThat(html.split("src=\"data:image/png;base64,", -1)).hasSize(51);
		System.out.printf("NFR-09: 50-step report with %d KB screenshots: %d ms, %d bytes%n", SCREENSHOT_BYTES / 1024,
				elapsedMs, html.length());
	}

	record SavedTest(String id, List<String> stepIds) {
	}

	private SavedTest test(String name, int steps) throws Exception {
		String testId = id(mvc.perform(post("/api/apps/{id}/tests", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", name)))));
		Map<String, Object> click = Map.of("keyword", "Click", "target", "login.loginButton");
		String saved = mvc
			.perform(put("/api/tests/{id}/steps", testId).contentType(MediaType.APPLICATION_JSON)
				.content(mapper.writeValueAsString(
						Map.of("version", stepSchema.version(), "steps", Collections.nCopies(steps, click)))))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();
		return new SavedTest(testId, JsonPath.read(saved, "$.document.steps[*].id"));
	}

	private String report(String runId, String lang) throws Exception {
		var call = get("/api/runs/{id}/report.html", runId);
		if (!lang.isEmpty()) {
			call.param("lang", lang);
		}
		MvcResult started = mvc.perform(call).andExpect(request().asyncStarted()).andReturn();
		return mvc.perform(asyncDispatch(started))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString(StandardCharsets.UTF_8);
	}

	/** A PNG signature followed by `size` bytes that do not compress, different for every seed. */
	private static byte[] png(int seed, int size) {
		byte[] signature = { (byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n' };
		byte[] png = Arrays.copyOf(signature, signature.length + size);
		byte[] body = new byte[size];
		new Random(seed).nextBytes(body);
		System.arraycopy(body, 0, png, signature.length, size);
		return png;
	}

	private String startRun(String testId) throws Exception {
		return id(mvc.perform(post("/api/runs").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("testId", testId, "appVersionId", versionId)))));
	}

	private static Map<String, Object> body(String runId, int index, String stepId, String status) {
		Map<String, Object> body = new HashMap<>();
		body.put("runId", runId);
		body.put("stepIndex", index);
		body.put("stepId", stepId);
		body.put("status", status);
		return body;
	}

	private ResultActions result(String runId, int index, String stepId, String status) throws Exception {
		return mvc.perform(put("/api/runs/{id}/results/{index}", runId, index).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(body(runId, index, stepId, status))));
	}

	private ResultActions upload(String runId, int index, byte[] png) throws Exception {
		return mvc.perform(
				put("/api/runs/{id}/results/{i}/screenshot", runId, index).contentType(MediaType.IMAGE_PNG).content(png));
	}

	private void finish(String runId, String status) throws Exception {
		mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("status", status)))).andExpect(status().isOk());
	}

	private static String id(ResultActions created) throws Exception {
		return JsonPath.read(created.andReturn().getResponse().getContentAsString(), "$.id");
	}

}
