package com.ayna.server.runs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import org.junit.jupiter.api.Test;

import com.ayna.server.auth.UserRef;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.runs.RunDtos.RunDetail;
import com.ayna.server.runs.RunDtos.StepResultResponse;
import com.ayna.server.runs.RunReport.Lang;
import com.ayna.server.runs.RunReport.Words;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;

/** The report's HTML without Spring or a database (#59). */
class RunReportTest {

	static final ObjectMapper MAPPER = JsonMapper.builder().build();

	static final Instant STARTED = Instant.parse("2026-11-10T12:00:00Z");

	static final byte[] PNG = { (byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n', 1, 2, 3 };

	static final String STEPS = """
			{"version": "0.2", "steps": [
			  {"keyword": "Type", "target": "login.userNameInput", "value": "admin"},
			  {"keyword": "Click", "target": "login.loginButton"},
			  {"keyword": "Verify", "target": "main.welcomeLabel",
			   "checkpoint": {"property": "name", "operator": "equals", "expected": "Welcome, admin!"}},
			  {"keyword": "Wait", "target": "main.window"}
			]}""";

	@Test
	void showsEveryStepWithItsScreenshotStatusDurationAndMessage() {
		String html = render(Lang.EN, Map.of(0, PNG, 1, PNG, 2, PNG),
				result(0, "passed", 120L, null), result(1, "passed", 2500L, null),
				result(2, "failed", 40L, "Expected 'Welcome, admin!', found 'Wrong password'"));

		assertThat(html).startsWith("<!DOCTYPE html>")
			.contains("<title>Run report · Giriş</title>")
			.contains("Type text · login.userNameInput · “admin”")
			.contains("Click · login.loginButton")
			.contains("Check · main.welcomeLabel · Text is “Welcome, admin!”")
			.contains("Wait for · main.window")
			.contains("120 ms")
			.contains("2.5 s")
			.contains("Expected &#39;Welcome, admin!&#39;, found &#39;Wrong password&#39;")
			.contains("<a href=\"#step-3\">First failed step: 3</a>");
		String encoded = Base64.getEncoder().encodeToString(PNG);
		assertThat(Pattern.compile("src=\"data:image/png;base64," + Pattern.quote(encoded) + "\"").matcher(html).results())
			.hasSize(3);
		assertThat(html).contains("<tbody id=\"step-4\" class=\"missing\">")
			.contains("No screenshot for this step")
			.contains("<dd>4 · <span class=\"passed-text\">2 passed</span> · <span class=\"failed-text\">1 failed</span>"
					+ " · 0 not run · 1 no result</dd>");
	}

	@Test
	void loadsNothingFromOutsideTheFile() {
		String html = render(Lang.EN, Map.of(0, PNG), result(0, "passed", 1L, null));

		assertThat(html).contains("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
				+ "img-src data:; style-src 'unsafe-inline'\">");
		assertThat(html).doesNotContainPattern("(?i)(src|href)\\s*=\\s*\"(?!data:|#)")
			.doesNotContainPattern("(?i)url\\(")
			.doesNotContainPattern("(?i)@import")
			.doesNotContainPattern("(?i)<script")
			.doesNotContainPattern("(?i)<link");
	}

	@Test
	void escapesWhatCameFromTheAgentAndTheUser() {
		String html = RunReport.render(
				new RunReport.Input(run("failed", List.of(result(0, "failed", 1L, "<img src=x onerror=alert(1)>"))),
						"<b>name</b>", "App & Co", "1.0\"", step -> null),
				Lang.EN, STARTED, ZoneOffset.UTC);

		assertThat(html).doesNotContain("<img src=x").doesNotContain("<b>name</b>")
			.contains("&lt;img src=x onerror=alert(1)&gt;")
			.contains("&lt;b&gt;name&lt;/b&gt;")
			.contains("App &amp; Co 1.0&quot;");
	}

	@Test
	void speaksTurkishWhenAsked() {
		String html = render(Lang.TR, Map.of(), result(0, "passed", 2500L, null), result(1, "notRun", null, null));

		assertThat(html).contains("<html lang=\"tr\">")
			.contains("<title>Çalıştırma raporu · Giriş</title>")
			.contains("Yaz · login.userNameInput · “admin”")
			.contains("Kontrol et · main.welcomeLabel · Metin eşittir “Welcome, admin!”")
			.contains("2,5 sn")
			.contains("Bu adımın ekran görüntüsü yok")
			.contains("çalıştırılmadı")
			.contains("Sürüyor");
	}

	@Test
	void describesRowsAndEveryKindOfCheck() {
		assertThat(describe("{\"keyword\":\"SelectRow\",\"target\":\"main.entries\",\"row\":{\"index\":3}}"))
			.isEqualTo("Choose row · main.entries · row 3");
		assertThat(describe(
				"{\"keyword\":\"SelectRow\",\"target\":\"main.entries\",\"row\":{\"value\":\"Bank\",\"column\":\"Title\"}}"))
			.isEqualTo("Choose row · main.entries · row with “Bank” in Title");
		assertThat(describe("""
				{"keyword":"Verify","target":"main.entries","checkpoint":{"property":"cell","operator":"contains",
				 "expected":"Bank","row":{"index":2},"column":"Title"}}"""))
			.isEqualTo("Check · main.entries · Cell (row 2, Title) contains “Bank”");
		assertThat(describe("""
				{"keyword":"Verify","target":"main.entries","checkpoint":{"property":"rowExists","operator":"equals",
				 "expected":true,"row":{"value":"Bank"}}}"""))
			.isEqualTo("Check · main.entries · Row is listed (row with “Bank”) is yes");
		assertThat(describe("""
				{"keyword":"Verify","target":"main.entries","checkpoint":{"property":"rowCount","operator":"equals",
				 "expected":0}}"""))
			.isEqualTo("Check · main.entries · Number of rows is 0");
		assertThat(describe("{\"keyword\":\"Select\",\"target\":\"form.city\",\"value\":\"Ankara\"}"))
			.isEqualTo("Choose item · form.city · “Ankara”");
	}

	@Test
	void writesTimesWithTheirOffset() {
		String html = RunReport.render(
				new RunReport.Input(run("running", List.of()), "Giriş", "Müşteri Kayıt", "1.0.0", step -> null), Lang.EN,
				STARTED, ZoneId.of("Europe/Istanbul"));

		assertThat(html).contains("<dd>2026-11-10 15:00:00 (UTC+03:00)</dd>");
	}

	/** hasan's #229 review: one screenshot in memory at a time, not the whole report. */
	@Test
	void writesEachStepBeforeReadingTheNextScreenshot() throws Exception {
		ByteArrayOutputStream out = new ByteArrayOutputStream();
		List<Integer> asked = new ArrayList<>();
		RunReport.Input input = new RunReport.Input(
				run("failed", List.of(result(0, "passed", 1L, null), result(1, "passed", 1L, null),
						result(2, "failed", 1L, "x"))),
				"Giriş", "Müşteri Kayıt", "1.0.0", step -> {
					String written = out.toString(StandardCharsets.UTF_8);
					// The step's own row is out already, and the next step's is not.
					assertThat(written).contains("<tbody id=\"step-" + (step + 1) + "\"")
						.doesNotContain("<tbody id=\"step-" + (step + 2) + "\"");
					asked.add(step);
					return PNG;
				});

		RunReport.render(input, Lang.TR, STARTED, ZoneOffset.UTC, out);

		assertThat(asked).containsExactly(0, 1, 2, 3);
		String html = out.toString(StandardCharsets.UTF_8);
		assertThat(html).endsWith("</html>\n").contains("Çalıştırma raporu");
		assertThat(html.split("src=\"data:image/png;base64," + Pattern.quote(Base64.getEncoder().encodeToString(PNG))
				+ "\"", -1)).hasSize(5);
	}

	@Test
	void namesARepairProposedStepAndLinksToIt() {
		String html = render(Lang.TR, Map.of(), result(0, "passed", 1L, null),
				result(1, "repairProposed", 1L, "login.loginButton not found; 3 candidates"));

		assertThat(html).contains("<tbody id=\"step-2\" class=\"repairProposed\">")
			.contains(">onarım önerildi</span>")
			.contains("1 onarım önerildi")
			.contains("<a href=\"#step-2\">İlk başarısız adım: 2</a>")
			.contains("2 sonuç yok");
	}

	@Test
	void acceptsEnOrTrOnly() {
		assertThat(Lang.parse(null)).isEqualTo(Lang.EN);
		assertThat(Lang.parse("TR")).isEqualTo(Lang.TR);
		assertThatThrownBy(() -> Lang.parse("de")).isInstanceOf(InvalidRequestException.class);
	}

	@Test
	void theWholeFileIsUtf8Text() {
		String html = render(Lang.TR, Map.of(0, PNG), result(0, "passed", 1L, "Şifre doğru"));

		assertThat(new String(html.getBytes(StandardCharsets.UTF_8), StandardCharsets.UTF_8)).isEqualTo(html);
		assertThat(html).contains("<meta charset=\"utf-8\">").contains("Şifre doğru");
	}

	static String describe(String step) {
		return RunReport.describe(MAPPER.readTree(step), Words.EN);
	}

	static String render(Lang lang, Map<Integer, byte[]> screenshots, StepResultResponse... results) {
		boolean failed = List.of(results).stream().anyMatch(r -> r.status().equals("failed"));
		return RunReport.render(new RunReport.Input(run(failed ? "failed" : "running", List.of(results)), "Giriş",
				"Müşteri Kayıt", "1.0.0", screenshots::get), lang, STARTED.plusSeconds(60), ZoneOffset.UTC);
	}

	static RunDetail run(String status, List<StepResultResponse> results) {
		JsonNode document = MAPPER.readTree(STEPS);
		boolean ended = !status.equals("running");
		return new RunDetail("run-1", "test-1", "version-1", status, document.path("steps").size(),
				new UserRef("user-1", "admin"), STARTED, ended ? STARTED.plusSeconds(3) : null, ended ? 3000L : null,
				document, results);
	}

	static StepResultResponse result(int index, String status, Long durationMs, String message) {
		return new StepResultResponse("result-" + index, index, null, status, durationMs, message, STARTED,
				null);
	}

}
