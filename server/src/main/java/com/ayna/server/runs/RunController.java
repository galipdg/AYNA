package com.ayna.server.runs;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.util.List;

import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.CacheControl;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.util.unit.DataSize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.TooLargeException;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.runs.RunDtos.CreateRunRequest;
import com.ayna.server.runs.RunDtos.FinishRunRequest;
import com.ayna.server.runs.RunDtos.RunDetail;
import com.ayna.server.runs.RunDtos.RunSummary;
import com.ayna.server.runs.RunDtos.StepResultWritten;
import com.ayna.server.runs.RunService.ScreenshotWritten;
import com.ayna.server.runs.RunService.StoredResult;

import tools.jackson.databind.JsonNode;

/** Runs and their step results (#44, ADR runs-api-and-live-updates). */
@RestController
public class RunController {

	private final RunService service;

	private final long maxScreenshotBytes;

	public RunController(RunService service,
			@Value("${ayna.screenshots.max-size:8MB}") DataSize maxScreenshotSize) {
		this.service = service;
		this.maxScreenshotBytes = maxScreenshotSize.toBytes();
	}

	/** The response's `document` is what to play: results point into it by `stepIndex`. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND })
	@PostMapping("/api/runs")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<RunDetail> createRun(@RequestBody CreateRunRequest request,
			@AuthenticationPrincipal AynaPrincipal me) {
		RunDetail run = service.createRun(required(request.testId(), "testId"),
				required(request.appVersionId(), "appVersionId"), me.userId());
		return ResponseEntity.created(URI.create("/api/runs/" + run.id())).body(run);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/runs/{runId}")
	public RunDetail getRun(@PathVariable String runId) {
		return service.getRun(runId);
	}

	/** Newest first, at most 20. A client that opens a test reads `?status=running` to catch up. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND })
	@GetMapping("/api/tests/{testId}/runs")
	public List<RunSummary> listRuns(@PathVariable String testId, @RequestParam(required = false) String status) {
		return service.listRuns(testId, status);
	}

	/**
	 * The application's runs, newest first, at most 100: the run history screen (#68).
	 * `testId` and `status` narrow them.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND })
	@GetMapping("/api/apps/{appId}/runs")
	public List<RunSummary> listAppRuns(@PathVariable String appId, @RequestParam(required = false) String testId,
			@Parameter(schema = @Schema(
					allowableValues = { "running", "passed", "failed", "aborted" })) @RequestParam(
							required = false) String status) {
		return service.listAppRuns(appId, testId, status);
	}

	/**
	 * Body: the `params` of the agent's `run.stepResult`, unchanged (`docs/agent-rpc.md`). 201 on
	 * the first write; 200 for an identical repeat, which writes nothing.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@ApiResponse(responseCode = "201", description = "Stored")
	@ApiResponse(responseCode = "200", description = "Identical repeat; nothing was written",
			content = @Content(schema = @Schema(implementation = StepResultWritten.class)))
	@PutMapping("/api/runs/{runId}/results/{stepIndex}")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<StepResultWritten> writeResult(@PathVariable String runId, @PathVariable int stepIndex,
			@RequestBody JsonNode body) {
		StoredResult result = service.writeResult(runId, stepIndex, body);
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK)
			.body(new StepResultWritten(result.id()));
	}

	/**
	 * Body: the step's screenshot as `image/png`, sent after its result (#51). 201 on the first
	 * write; 200 for the same image again. Another image for the step is a 409.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT, HttpStatus.CONTENT_TOO_LARGE,
			HttpStatus.UNSUPPORTED_MEDIA_TYPE })
	@ApiResponse(responseCode = "201", description = "Stored")
	@ApiResponse(responseCode = "200", description = "The same image again; nothing was written",
			content = @Content(schema = @Schema(implementation = StepResultWritten.class)))
	@io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
			content = @Content(mediaType = MediaType.IMAGE_PNG_VALUE, schema = @Schema(type = "string", format = "binary")))
	@PutMapping(path = "/api/runs/{runId}/results/{stepIndex}/screenshot", consumes = MediaType.IMAGE_PNG_VALUE)
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<StepResultWritten> writeScreenshot(@PathVariable String runId, @PathVariable int stepIndex,
			HttpServletRequest request) throws IOException {
		if (request.getContentLengthLong() > maxScreenshotBytes) {
			throw new TooLargeException("A screenshot may have at most " + maxScreenshotBytes + " bytes, this one has "
					+ request.getContentLengthLong());
		}
		byte[] png;
		try (InputStream in = request.getInputStream()) {
			// One byte over the limit is enough to know the body is too large without reading all of it.
			png = in.readNBytes((int) Math.min(Integer.MAX_VALUE - 8, maxScreenshotBytes + 1));
		}
		ScreenshotWritten written = service.writeScreenshot(runId, stepIndex, png, maxScreenshotBytes);
		return ResponseEntity.status(written.created() ? HttpStatus.CREATED : HttpStatus.OK)
			.body(new StepResultWritten(written.stepResultId()));
	}

	/** The step's screenshot; a stored image never changes, so clients may keep it. */
	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@ApiResponse(responseCode = "200", description = "The PNG",
			content = @Content(mediaType = MediaType.IMAGE_PNG_VALUE, schema = @Schema(type = "string", format = "binary")))
	// No `produces`: a 404 must still be able to answer with a problem body.
	@GetMapping("/api/runs/{runId}/results/{stepIndex}/screenshot")
	public ResponseEntity<byte[]> readScreenshot(@PathVariable String runId, @PathVariable int stepIndex) {
		return ResponseEntity.ok()
			.contentType(MediaType.IMAGE_PNG)
			.cacheControl(CacheControl.maxAge(Duration.ofDays(1)).cachePrivate())
			.body(service.readScreenshot(runId, stepIndex));
	}

	/**
	 * The run's report as one self-contained HTML file (#59, FR-21), rendered from what is stored
	 * now, so every run has one in every state. `lang` is `en` (the default) or `tr`.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND })
	@ApiResponse(responseCode = "200", description = "The report",
			content = @Content(mediaType = MediaType.TEXT_HTML_VALUE, schema = @Schema(type = "string")))
	// No `produces`, as for the screenshot: a 404 still answers with a problem body.
	@GetMapping("/api/runs/{runId}/report.html")
	public ResponseEntity<String> runReport(@PathVariable String runId,
			@Parameter(schema = @Schema(allowableValues = { "en", "tr" }, defaultValue = "en")) @RequestParam(
					required = false) String lang) {
		RunReport.Lang language = RunReport.Lang.parse(lang);
		String html = RunReport.render(service.reportInput(runId), language, Instant.now(), ZoneId.systemDefault());
		return ResponseEntity.ok()
			.contentType(new MediaType(MediaType.TEXT_HTML, StandardCharsets.UTF_8))
			.cacheControl(CacheControl.noStore())
			.header(HttpHeaders.CONTENT_DISPOSITION,
					ContentDisposition.inline().filename("ayna-run-" + runId + ".html").build().toString())
			.header("Content-Security-Policy", RunReport.CONTENT_SECURITY_POLICY)
			.body(html);
	}

	/** Ends the run as passed, failed or aborted; the same status again answers 200. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/runs/{runId}/finish")
	public RunSummary finishRun(@PathVariable String runId, @RequestBody FinishRunRequest request) {
		return service.finishRun(runId, request.status());
	}

	/** Trims the value; a missing or blank value is a 400. */
	private static String required(String value, String field) {
		if (value == null || value.isBlank()) {
			throw new InvalidRequestException("$." + field, "'" + field + "' must not be blank");
		}
		return value.strip();
	}

}
