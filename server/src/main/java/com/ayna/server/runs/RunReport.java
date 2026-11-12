package com.ayna.server.runs;

import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;
import java.util.function.IntFunction;
import java.util.stream.Collectors;

import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.runs.RunDtos.RunDetail;
import com.ayna.server.runs.RunDtos.StepResultResponse;

import tools.jackson.databind.JsonNode;

/**
 * The HTML report of one run (#59, FR-21): a summary, a step table with status, duration and
 * message, and each step's screenshot, as one self-contained file. Styles are inline and
 * screenshots are `data:` URIs, so the file opens in a browser with no network; its Content
 * Security Policy forbids every other source, so it cannot load anything even by mistake.
 * <p>
 * It is written to a stream as it is made, one step at a time, and each screenshot is read only
 * when its step is written and encoded straight into the stream: the peak memory is one
 * screenshot, not the whole report (hasan, #229 review). Pure, so it is tested without Spring or
 * a database.
 */
final class RunReport {

	/** The policy of the report, as a `<meta>` in the file and as the response header. */
	static final String CONTENT_SECURITY_POLICY = "default-src 'none'; img-src data:; style-src 'unsafe-inline'";

	private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

	private RunReport() {
	}

	/**
	 * What a report shows. `screenshot` gives a step's PNG, or null when it has none; it is
	 * called once per step, in step order, while that step is written.
	 */
	record Input(RunDetail run, String testName, String applicationName, String version,
			IntFunction<byte[]> screenshot) {
	}

	/** The report's language. Agent messages are shown as they were sent, whatever it is. */
	enum Lang {

		EN, TR;

		/** `en` (also when absent) or `tr`; anything else is a 400. */
		static Lang parse(String value) {
			if (value == null || value.isBlank() || value.equalsIgnoreCase("en")) {
				return EN;
			}
			if (value.equalsIgnoreCase("tr")) {
				return TR;
			}
			throw new InvalidRequestException("A report is in en or tr, not '" + value + "'", List.of());
		}

	}

	/** The whole report as one string; for tests. */
	static String render(Input input, Lang lang, Instant generatedAt, ZoneId zone) {
		ByteArrayOutputStream out = new ByteArrayOutputStream();
		try {
			render(input, lang, generatedAt, zone, out);
		}
		catch (IOException ex) {
			throw new UncheckedIOException(ex);
		}
		return out.toString(StandardCharsets.UTF_8);
	}

	/** Writes the report to `out` as UTF-8 and flushes it; `out` stays open. */
	static void render(Input input, Lang lang, Instant generatedAt, ZoneId zone, OutputStream out)
			throws IOException {
		OutputStream target = new KeptOpen(out);
		Writer writer = new BufferedWriter(new OutputStreamWriter(target, StandardCharsets.UTF_8), 16 * 1024);
		Words w = lang == Lang.TR ? Words.TR : Words.EN;
		RunDetail run = input.run();
		Map<Integer, StepResultResponse> results = run.results()
			.stream()
			.collect(Collectors.toMap(StepResultResponse::stepIndex, Function.identity()));
		JsonNode steps = run.document().path("steps");
		int passed = 0;
		int failed = 0;
		int notRun = 0;
		int repairProposed = 0;
		Integer firstFailure = null;
		for (int i = 0; i < run.stepCount(); i++) {
			StepResultResponse result = results.get(i);
			String status = result == null ? "" : result.status();
			switch (status) {
				case "passed" -> passed++;
				case "failed" -> failed++;
				case "notRun" -> notRun++;
				case "repairProposed" -> repairProposed++;
				default -> {
				}
			}
			if (firstFailure == null && (status.equals("failed") || status.equals("repairProposed"))) {
				firstFailure = i;
			}
		}
		int missing = run.stepCount() - passed - failed - notRun - repairProposed;

		// Built a step at a time and written out, so it never holds more than one step's text.
		StringBuilder html = new StringBuilder(8 * 1024);
		html.append("<!DOCTYPE html>\n<html lang=\"")
			.append(lang.name().toLowerCase(Locale.ROOT))
			.append("\">\n<head>\n<meta charset=\"utf-8\">\n")
			.append("<meta http-equiv=\"Content-Security-Policy\" content=\"")
			.append(CONTENT_SECURITY_POLICY)
			.append("\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>")
			.append(esc(w.title + " · " + input.testName()))
			.append("</title>\n<style>")
			.append(CSS)
			.append("</style>\n</head>\n<body>\n<header>\n<p class=\"brand\">AYNA · ")
			.append(esc(w.title))
			.append("</p>\n<h1>")
			.append(esc(input.testName()))
			.append(" <span class=\"badge ")
			.append(esc(run.status()))
			.append("\">")
			.append(esc(w.runStatus(run.status())))
			.append("</span></h1>\n</header>\n<main>\n<section class=\"summary\">\n<dl>\n");
		term(html, w.application, input.applicationName() + " " + input.version());
		term(html, w.startedBy, run.startedBy().username() != null ? run.startedBy().username() : run.startedBy().id());
		term(html, w.started, time(run.startedAt(), zone));
		term(html, w.finished, run.finishedAt() == null ? "–" : time(run.finishedAt(), zone));
		term(html, w.duration, run.durationMs() == null ? "–" : duration(run.durationMs(), w));
		html.append("<dt>")
			.append(esc(w.steps))
			.append("</dt><dd>")
			.append(run.stepCount())
			.append(" · <span class=\"passed-text\">")
			.append(passed)
			.append(' ')
			.append(esc(w.resultStatus("passed")))
			.append("</span> · <span class=\"failed-text\">")
			.append(failed)
			.append(' ')
			.append(esc(w.resultStatus("failed")))
			.append("</span> · ")
			.append(notRun)
			.append(' ')
			.append(esc(w.resultStatus("notRun")));
		if (repairProposed > 0) {
			html.append(" · ").append(repairProposed).append(' ').append(esc(w.resultStatus("repairProposed")));
		}
		if (missing > 0) {
			html.append(" · ").append(missing).append(' ').append(esc(w.resultStatus(null)));
		}
		html.append("</dd>\n</dl>\n");
		if (firstFailure != null) {
			html.append("<p class=\"jump\"><a href=\"#step-")
				.append(firstFailure + 1)
				.append("\">")
				.append(esc(w.firstFailure(firstFailure + 1)))
				.append("</a></p>\n");
		}
		html.append("</section>\n<section>\n<h2>")
			.append(esc(w.steps))
			.append("</h2>\n<table>\n<thead><tr><th>#</th><th>")
			.append(esc(w.step))
			.append("</th><th>")
			.append(esc(w.status))
			.append("</th><th>")
			.append(esc(w.duration))
			.append("</th><th>")
			.append(esc(w.message))
			.append("</th></tr></thead>\n");
		for (int i = 0; i < run.stepCount(); i++) {
			StepResultResponse result = results.get(i);
			String status = result == null ? "missing" : result.status();
			html.append("<tbody id=\"step-")
				.append(i + 1)
				.append("\" class=\"")
				.append(esc(status))
				.append("\">\n<tr><td class=\"n\">")
				.append(i + 1)
				.append("</td><td>")
				.append(esc(describe(steps.path(i), w)))
				.append("</td><td><span class=\"badge ")
				.append(esc(status))
				.append("\">")
				.append(esc(w.resultStatus(result == null ? null : result.status())))
				.append("</span></td><td class=\"n\">")
				.append(result == null || result.durationMs() == null ? "–" : esc(duration(result.durationMs(), w)))
				.append("</td><td class=\"msg\">")
				.append(result == null || result.message() == null ? "" : esc(result.message()))
				.append("</td></tr>\n<tr class=\"shot\"><td></td><td colspan=\"4\">");
			// The step is out before its screenshot is read, so the client sees it arrive.
			emit(html, writer);
			writer.flush();
			byte[] png = input.screenshot().apply(i);
			if (png != null) {
				html.append("<img alt=\"")
					.append(esc(w.screenshotOf(i + 1)))
					.append("\" src=\"data:image/png;base64,");
				emit(html, writer);
				writer.flush();
				// Encoded through to the stream: no base64 copy of the image is ever held.
				try (OutputStream base64 = Base64.getEncoder().wrap(target)) {
					base64.write(png);
				}
				html.append("\">");
			}
			else {
				html.append("<p class=\"none\">").append(esc(w.noScreenshot)).append("</p>");
			}
			html.append("</td></tr>\n</tbody>\n");
			emit(html, writer);
		}
		html.append("</table>\n</section>\n</main>\n<footer>")
			.append(esc(w.generated(time(generatedAt, zone), run.id())))
			.append("</footer>\n</body>\n</html>\n");
		emit(html, writer);
		writer.flush();
	}

	/** Writes what `html` holds and empties it. */
	private static void emit(StringBuilder html, Writer writer) throws IOException {
		writer.append(html);
		html.setLength(0);
	}

	/**
	 * The response stream as the report's writers see it: closing them (the base64 encoder must be
	 * closed to write its padding) flushes it but leaves it open for the rest of the report.
	 */
	private static final class KeptOpen extends OutputStream {

		private final OutputStream out;

		KeptOpen(OutputStream out) {
			this.out = out;
		}

		@Override
		public void write(int b) throws IOException {
			out.write(b);
		}

		@Override
		public void write(byte[] bytes, int offset, int length) throws IOException {
			out.write(bytes, offset, length);
		}

		@Override
		public void flush() throws IOException {
			out.flush();
		}

		@Override
		public void close() throws IOException {
			out.flush();
		}

	}

	/** One line for a step, in the step editor's words: keyword, target and what it uses. */
	static String describe(JsonNode step, Words w) {
		String keyword = step.path("keyword").asString("");
		StringBuilder text = new StringBuilder(w.keyword(keyword)).append(" · ").append(step.path("target").asString(""));
		switch (keyword) {
			case "Type", "Select" -> text.append(" · “").append(step.path("value").asString("")).append('”');
			case "SelectRow" -> text.append(" · ").append(row(step.path("row"), w));
			case "Verify" -> text.append(" · ").append(check(step.path("checkpoint"), w));
			default -> {
			}
		}
		return text.toString();
	}

	private static String check(JsonNode checkpoint, Words w) {
		String property = checkpoint.path("property").asString("");
		JsonNode expected = checkpoint.path("expected");
		String value = expected.isBoolean() ? (expected.asBoolean() ? w.yes : w.no)
				: expected.isNumber() ? expected.asString() : "“" + expected.asString("") + "”";
		String subject = w.property(property);
		if (property.equals("cell")) {
			subject += " (" + row(checkpoint.path("row"), w) + ", " + checkpoint.path("column").asString("") + ")";
		}
		else if (property.equals("rowExists")) {
			subject += " (" + row(checkpoint.path("row"), w) + ")";
		}
		return subject + " " + w.operator(checkpoint.path("operator").asString("")) + " " + value;
	}

	private static String row(JsonNode row, Words w) {
		if (row.has("index")) {
			return w.rowNumber(row.path("index").asString());
		}
		return w.rowWithText(row.path("value").asString(""), row.path("column").asString(""));
	}

	private static void term(StringBuilder html, String term, String value) {
		html.append("<dt>").append(esc(term)).append("</dt><dd>").append(esc(value)).append("</dd>\n");
	}

	private static String time(Instant instant, ZoneId zone) {
		var local = instant.atZone(zone);
		return TIME.format(local) + " (UTC" + (local.getOffset().getTotalSeconds() == 0 ? "" : local.getOffset())
				+ ")";
	}

	static String duration(long ms, Words w) {
		if (ms < 1000) {
			return ms + " ms";
		}
		return String.format(w.locale, "%.1f %s", ms / 1000.0, w.seconds);
	}

	/** Escapes text for HTML content and double-quoted attributes. */
	static String esc(String text) {
		if (text == null) {
			return "";
		}
		StringBuilder out = new StringBuilder(text.length() + 16);
		for (int i = 0; i < text.length(); i++) {
			char c = text.charAt(i);
			switch (c) {
				case '&' -> out.append("&amp;");
				case '<' -> out.append("&lt;");
				case '>' -> out.append("&gt;");
				case '"' -> out.append("&quot;");
				case '\'' -> out.append("&#39;");
				default -> out.append(c);
			}
		}
		return out.toString();
	}

	/**
	 * The report's words. Keyword, property and operator labels are the client's step editor's
	 * (`client/src/renderer/src/i18n`), so a report reads like the test it came from.
	 */
	static final class Words {

		static final Words EN = new Words(Locale.ENGLISH, "Run report", "Application", "Started by", "Started",
				"Finished", "Duration", "Steps", "Step", "Status", "Message", "No screenshot for this step", "yes", "no",
				"s",
				Map.of("Click", "Click", "Type", "Type text", "Select", "Choose item", "SelectRow", "Choose row",
						"Verify", "Check", "Wait", "Wait for"),
				Map.of("name", "Text", "value", "Field content", "enabled", "Enabled", "visible", "On screen", "checked",
						"Checked", "selected", "Selected", "cell", "Cell", "rowExists", "Row is listed", "rowCount",
						"Number of rows"),
				Map.of("equals", "is", "notEquals", "is not", "contains", "contains"),
				Map.of("running", "Running", "passed", "Passed", "failed", "Failed", "aborted", "Aborted"),
				Map.of("passed", "passed", "failed", "failed", "notRun", "not run", "repairProposed", "repair proposed"),
				"no result");

		static final Words TR = new Words(Locale.forLanguageTag("tr"), "Çalıştırma raporu", "Uygulama", "Başlatan",
				"Başlangıç", "Bitiş", "Süre", "Adımlar", "Adım", "Durum", "Mesaj", "Bu adımın ekran görüntüsü yok", "evet",
				"hayır", "sn",
				Map.of("Click", "Tıkla", "Type", "Yaz", "Select", "Listeden seç", "SelectRow", "Satır seç", "Verify",
						"Kontrol et", "Wait", "Bekle"),
				Map.of("name", "Metin", "value", "Alan içeriği", "enabled", "Etkin", "visible", "Ekranda", "checked",
						"İşaretli", "selected", "Seçili", "cell", "Hücre", "rowExists", "Satır listede", "rowCount",
						"Satır sayısı"),
				Map.of("equals", "eşittir", "notEquals", "eşit değildir", "contains", "içerir"),
				Map.of("running", "Sürüyor", "passed", "Başarılı", "failed", "Başarısız", "aborted", "Yarıda kesildi"),
				Map.of("passed", "başarılı", "failed", "başarısız", "notRun", "çalıştırılmadı", "repairProposed",
						"onarım önerildi"),
				"sonuç yok");

		final Locale locale;

		final String title;

		final String application;

		final String startedBy;

		final String started;

		final String finished;

		final String duration;

		final String steps;

		final String step;

		final String status;

		final String message;

		final String noScreenshot;

		final String yes;

		final String no;

		final String seconds;

		private final Map<String, String> keywords;

		private final Map<String, String> properties;

		private final Map<String, String> operators;

		private final Map<String, String> runStatuses;

		private final Map<String, String> resultStatuses;

		private final String noResult;

		private Words(Locale locale, String title, String application, String startedBy, String started,
				String finished, String duration, String steps, String step, String status, String message,
				String noScreenshot, String yes, String no, String seconds, Map<String, String> keywords,
				Map<String, String> properties, Map<String, String> operators, Map<String, String> runStatuses,
				Map<String, String> resultStatuses, String noResult) {
			this.locale = locale;
			this.title = title;
			this.application = application;
			this.startedBy = startedBy;
			this.started = started;
			this.finished = finished;
			this.duration = duration;
			this.steps = steps;
			this.step = step;
			this.status = status;
			this.message = message;
			this.noScreenshot = noScreenshot;
			this.yes = yes;
			this.no = no;
			this.seconds = seconds;
			this.keywords = keywords;
			this.properties = properties;
			this.operators = operators;
			this.runStatuses = runStatuses;
			this.resultStatuses = resultStatuses;
			this.noResult = noResult;
		}

		String keyword(String keyword) {
			return keywords.getOrDefault(keyword, keyword);
		}

		String property(String property) {
			return properties.getOrDefault(property, property);
		}

		String operator(String operator) {
			return operators.getOrDefault(operator, operator);
		}

		String runStatus(String status) {
			return runStatuses.getOrDefault(status, status);
		}

		/** A step's status; null is a step with no stored result. */
		String resultStatus(String status) {
			return status == null ? noResult : resultStatuses.getOrDefault(status, status);
		}

		String rowNumber(String index) {
			return this == TR ? index + ". satır" : "row " + index;
		}

		String rowWithText(String value, String column) {
			if (this == TR) {
				return column.isEmpty() ? "bir hücresi “" + value + "” olan satır"
						: column + " sütunu “" + value + "” olan satır";
			}
			return column.isEmpty() ? "row with “" + value + "”" : "row with “" + value + "” in " + column;
		}

		String firstFailure(int step) {
			return this == TR ? "İlk başarısız adım: " + step : "First failed step: " + step;
		}

		String screenshotOf(int step) {
			return this == TR ? step + ". adımın ekran görüntüsü" : "Screenshot of step " + step;
		}

		String generated(String time, String runId) {
			return this == TR ? "AYNA, " + time + " · çalıştırma " + runId
					: "Generated by AYNA, " + time + " · run " + runId;
		}

	}

	private static final String CSS = """
			:root{color-scheme:light dark;--fg:#1d1d1f;--muted:#6b6b70;--bg:#fff;--line:#e3e3e8;--head:#f6f6f8;\
			--pass:#1a7f37;--fail:#c62828;--warn:#9a6700;--none:#6b6b70}
			@media (prefers-color-scheme:dark){:root{--fg:#ececf0;--muted:#a0a0a8;--bg:#18181b;--line:#33333a;\
			--head:#222227;--pass:#4ac26b;--fail:#ff6b6b;--warn:#e3b341;--none:#a0a0a8}}
			*{box-sizing:border-box}
			body{margin:0;padding:24px;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--fg);\
			background:var(--bg)}
			header,main,footer{max-width:1100px;margin:0 auto}
			.brand{margin:0;color:var(--muted);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
			h1{margin:4px 0 16px;font-size:22px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
			h2{font-size:16px;margin:24px 0 8px}
			dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0}
			dt{color:var(--muted)}dd{margin:0}
			.jump{margin:12px 0 0}.jump a{color:var(--fail)}
			table{width:100%;border-collapse:collapse}
			th,td{padding:6px 8px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
			thead th{background:var(--head);font-weight:600}
			td.n{white-space:nowrap;font-variant-numeric:tabular-nums}
			td.msg{white-space:pre-wrap;word-break:break-word}
			tr.shot td{border-bottom:2px solid var(--line);padding-bottom:12px}
			tr.shot img{display:block;max-width:100%;max-height:420px;border:1px solid var(--line)}
			tbody.failed tr:first-child td{background:color-mix(in srgb,var(--fail) 8%,transparent)}
			.none{margin:0;color:var(--muted);font-style:italic}
			.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;\
			border:1px solid currentColor;white-space:nowrap}
			.badge::first-letter{text-transform:uppercase}
			.passed,.passed-text{color:var(--pass)}.failed,.failed-text{color:var(--fail)}
			.running,.aborted,.repairProposed{color:var(--warn)}.notRun,.missing{color:var(--none)}
			tbody.passed,tbody.failed,tbody.notRun,tbody.missing,tbody.repairProposed{color:inherit}
			tbody.repairProposed tr:first-child td{background:color-mix(in srgb,var(--warn) 8%,transparent)}
			footer{margin-top:24px;color:var(--muted);font-size:12px}
			@media print{body{padding:0}tr.shot img{max-height:none}tbody{break-inside:avoid}}
			""";

}
