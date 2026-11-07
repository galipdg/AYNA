package com.ayna.server.runs;

import java.net.URI;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
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
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.runs.RunDtos.CreateRunRequest;
import com.ayna.server.runs.RunDtos.FinishRunRequest;
import com.ayna.server.runs.RunDtos.RunDetail;
import com.ayna.server.runs.RunDtos.RunSummary;
import com.ayna.server.runs.RunDtos.StepResultWritten;
import com.ayna.server.runs.RunService.StoredResult;

import tools.jackson.databind.JsonNode;

/** Runs and their step results (#44, ADR runs-api-and-live-updates). */
@RestController
public class RunController {

	private final RunService service;

	public RunController(RunService service) {
		this.service = service;
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
