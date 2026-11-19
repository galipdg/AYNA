package com.ayna.server.runs;

import java.time.Instant;
import java.util.List;

import tools.jackson.databind.JsonNode;

import com.ayna.server.auth.UserRef;

/** Request and response bodies of the runs API, and the messages on `/ws/runs`. */
final class RunDtos {

	private RunDtos() {
	}

	record CreateRunRequest(String testId, String appVersionId) {
	}

	record FinishRunRequest(String status) {
	}

	/** `durationMs` and `finishedAt` are null while the run is `running`. */
	record RunSummary(String id, String testId, String appVersionId, String status, int stepCount, UserRef startedBy,
			Instant startedAt, Instant finishedAt, Long durationMs) {
	}

	/**
	 * `document` is the step document copied when the run started; a result's `stepIndex` is a
	 * position in it, so editing the test later does not change what a result means.
	 */
	record RunDetail(String id, String testId, String appVersionId, String status, int stepCount, UserRef startedBy,
			Instant startedAt, Instant finishedAt, Long durationMs, JsonNode document,
			List<StepResultResponse> results) {
	}

	/**
	 * `screenshotUrl` is where the step's PNG is read, or null while it has none (#51). `category`
	 * says why a failed step failed (FR-35, #63), or is null: any other step, or the agent did not say.
	 */
	record StepResultResponse(String id, int stepIndex, String stepId, String status, Long durationMs, String message,
			Instant receivedAt, String screenshotUrl, String category) {
	}

	/** `healingProposalId` is the proposal a repairProposed result created (#74); null for any other result. */
	record StepResultWritten(String stepResultId, String healingProposalId) {
	}

	/** Messages from the server on `/ws/runs`; `type` tells them apart. */
	static final class Events {

		static final String SUBSCRIBED = "subscribed";

		static final String RUN_STARTED = "run.started";

		static final String STEP_RESULT = "run.stepResult";

		static final String RUN_FINISHED = "run.finished";

		static final String ERROR = "error";

		private Events() {
		}

		record Subscribed(String type, String testId) {
		}

		record RunChanged(String type, String testId, RunSummary run) {
		}

		record StepResult(String type, String testId, String runId, int stepIndex, String stepId, String status,
				Long durationMs, String message, String category) {
		}

		record Error(String type, String detail) {
		}

	}

}
