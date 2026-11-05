package com.ayna.server.runs;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionContext;
import org.neo4j.driver.Value;
import org.neo4j.driver.exceptions.ClientException;
import org.springframework.stereotype.Service;

import com.ayna.server.auth.UserRef;
import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.NotFoundException;
import com.ayna.server.error.FieldError;
import com.ayna.server.runs.RunDtos.Events;
import com.ayna.server.runs.RunDtos.RunDetail;
import com.ayna.server.runs.RunDtos.RunSummary;
import com.ayna.server.runs.RunDtos.StepResultResponse;
import com.ayna.server.tests.TestService;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/**
 * Runs and their step results (#44, ADR runs-api-and-live-updates). A run keeps a copy of the
 * test's steps, so a result's `stepIndex` stays true when the test is edited later. Writes are
 * safe to repeat: the client's outbox retries them. What other clients see goes out on
 * `/ws/runs` after the transaction commits, and only for writes that changed something.
 */
@Service
public class RunService {

	static final int HISTORY_LIMIT = 20;

	private static final String RUNNING = "running";

	private static final String PASSED = "passed";

	private static final String FAILED = "failed";

	private static final String ABORTED = "aborted";

	private static final String NOT_RUN = "notRun";

	/** Added by #51 and #74, which store the proposal that comes with it. */
	private static final String REPAIR_PROPOSED = "repairProposed";

	private static final Set<String> RUN_STATUSES = Set.of(RUNNING, PASSED, FAILED, ABORTED);

	private static final Set<String> FINISH_STATUSES = Set.of(PASSED, FAILED, ABORTED);

	private static final Set<String> RESULT_STATUSES = Set.of(PASSED, FAILED, NOT_RUN);

	/** What Neo4j reports when a uniqueness constraint refuses a write. */
	private static final String CONSTRAINT_FAILED = "Neo.ClientError.Schema.ConstraintValidationFailed";

	private static final String RUN_FIELDS = """
			OPTIONAL MATCH (u:User {id: r.startedBy})
			RETURN r, t.id AS testId, v.id AS appVersionId, u.username AS username""";

	private final Driver driver;

	private final TestService tests;

	private final RunEvents events;

	private final ObjectMapper mapper;

	public RunService(Driver driver, TestService tests, RunEvents events, ObjectMapper mapper) {
		this.driver = driver;
		this.tests = tests;
		this.events = events;
		this.mapper = mapper;
	}

	/** Starts a run of the test on an app version. `userId` is who started it (FR-40). */
	public RunDetail createRun(String testId, String appVersionId, String userId) {
		RunDetail run;
		try (Session session = driver.session()) {
			run = session.executeWrite(tx -> {
				requireSameApplication(tx, testId, appVersionId);
				JsonNode document = tests.stepDocument(tx, testId);
				int stepCount = document.path("steps").size();
				if (stepCount == 0) {
					throw new InvalidRequestException("$.testId", "Test " + testId + " has no steps to run");
				}
				String id = UUID.randomUUID().toString();
				tx.run("""
						MATCH (t:TestCase {id: $testId}), (v:AppVersion {id: $appVersionId})
						CREATE (r:Run {id: $id, status: $status, stepCount: $stepCount, document: $document,
						  startedBy: $userId, startedAt: datetime()})
						CREATE (r)-[:OF]->(t)
						CREATE (r)-[:ON_VERSION]->(v)""",
						Map.of("testId", testId, "appVersionId", appVersionId, "id", id, "status", RUNNING, "stepCount",
								stepCount, "document", mapper.writeValueAsString(document), "userId", userId))
					.consume();
				return detail(tx, id);
			});
		}
		events.publish(testId, new Events.RunChanged(Events.RUN_STARTED, testId, summary(run)));
		return run;
	}

	public RunDetail getRun(String runId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> detail(tx, runId));
		}
	}

	/** The test's runs, newest first; `status` narrows them, as a client catching up does. */
	public List<RunSummary> listRuns(String testId, String status) {
		if (status != null && !RUN_STATUSES.contains(status)) {
			throw new InvalidRequestException("Unknown run status: " + status, List.of());
		}
		Map<String, Object> params = new HashMap<>();
		params.put("testId", testId);
		params.put("status", status);
		params.put("limit", HISTORY_LIMIT);
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				if (!tx.run("MATCH (t:TestCase {id: $testId}) RETURN t LIMIT 1", params).hasNext()) {
					throw new NotFoundException("Test not found: " + testId);
				}
				return tx.run("""
						MATCH (r:Run)-[:OF]->(t:TestCase {id: $testId})
						WHERE $status IS NULL OR r.status = $status
						MATCH (r)-[:ON_VERSION]->(v:AppVersion)
						""" + RUN_FIELDS + " ORDER BY r.startedAt DESC LIMIT $limit", params).list(RunService::summary);
			});
		}
	}

	/**
	 * Stores one step's result: the `params` of the agent's `run.stepResult`, unchanged. An
	 * identical repeat changes nothing; another body for the same step is a 409. Members this
	 * version does not read stay in the stored body (#40, #54 and #63 add their own).
	 */
	public StoredResult writeResult(String runId, int stepIndex, JsonNode body) {
		checkBody(runId, stepIndex, body);
		String canonical = mapper.writeValueAsString(sorted(body));
		String hash = sha256(canonical);
		Stored stored;
		try {
			stored = store(runId, stepIndex, body, canonical, hash);
		}
		catch (ClientException ex) {
			if (!CONSTRAINT_FAILED.equals(ex.code())) {
				throw ex;
			}
			// An overlapping retry committed first, so this write is now a repeat of it.
			stored = store(runId, stepIndex, body, canonical, hash);
		}
		if (stored.created()) {
			events.publish(stored.testId(),
					new Events.StepResult(Events.STEP_RESULT, stored.testId(), runId, stepIndex, text(body, "stepId"),
							body.path("status").asString(), number(body, "duration"), text(body, "message")));
		}
		return new StoredResult(stored.id(), stored.created());
	}

	/**
	 * Ends the run. The status has to fit the stored results: `passed` needs every step passed,
	 * `failed` needs a failed step, and `aborted` is always allowed because a crash leaves gaps.
	 * The same status again is a repeat.
	 */
	public RunSummary finishRun(String runId, String status) {
		if (status == null || !FINISH_STATUSES.contains(status)) {
			throw new InvalidRequestException("$.status", "A run finishes as passed, failed or aborted, not " + status);
		}
		Finished finished;
		try (Session session = driver.session()) {
			finished = session.executeWrite(tx -> {
				RunDetail run = detail(tx, runId);
				if (run.status().equals(status)) {
					return new Finished(summary(run), false);
				}
				if (!run.status().equals(RUNNING)) {
					throw new ConflictException("Run " + runId + " already ended as " + run.status());
				}
				requireFits(run, status);
				tx.run("""
						MATCH (r:Run {id: $id})
						WITH r, datetime() AS now
						SET r.status = $status, r.finishedAt = now,
						  r.duration = duration.inSeconds(r.startedAt, now).milliseconds""",
						Map.of("id", runId, "status", status))
					.consume();
				return new Finished(summary(detail(tx, runId)), true);
			});
		}
		if (finished.changed()) {
			String testId = finished.run().testId();
			events.publish(testId, new Events.RunChanged(Events.RUN_FINISHED, testId, finished.run()));
		}
		return finished.run();
	}

	private Stored store(String runId, int stepIndex, JsonNode body, String canonical, String hash) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				Record run = runRecord(tx, runId);
				String testId = run.get("testId").asString();
				var existing = tx.run("""
						MATCH (:Run {id: $runId})-[:HAS_RESULT]->(sr:StepResult {stepIndex: $stepIndex})
						RETURN sr.id AS id, sr.bodyHash AS hash""", Map.of("runId", runId, "stepIndex", stepIndex));
				if (existing.hasNext()) {
					Record stored = existing.next();
					if (!stored.get("hash").asString().equals(hash)) {
						throw new ConflictException(
								"Step " + stepIndex + " of run " + runId + " already has a different result");
					}
					return new Stored(stored.get("id").asString(), testId, false);
				}
				String stepId = text(body, "stepId");
				checkAgainstRun(run.get("r"), stepIndex, stepId);
				if (!run.get("r").get("status").asString().equals(RUNNING)) {
					throw new ConflictException("Run " + runId + " has already ended");
				}
				String id = UUID.randomUUID().toString();
				Map<String, Object> params = new HashMap<>();
				params.put("runId", runId);
				params.put("id", id);
				params.put("stepIndex", stepIndex);
				params.put("stepId", stepId);
				params.put("status", body.path("status").asString());
				params.put("duration", number(body, "duration"));
				params.put("message", text(body, "message"));
				params.put("hash", hash);
				params.put("body", canonical);
				tx.run("""
						MATCH (r:Run {id: $runId})
						CREATE (r)-[:HAS_RESULT]->(:StepResult {id: $id, runId: $runId, stepIndex: $stepIndex,
						  stepId: $stepId, status: $status, duration: $duration, message: $message,
						  bodyHash: $hash, body: $body, receivedAt: datetime()})""", params).consume();
				// No link if the step was deleted after the run started; `stepIndex` still points into the copy.
				if (stepId != null) {
					tx.run("""
							MATCH (sr:StepResult {id: $id}), (s:Step {id: $stepId})
							CREATE (sr)-[:FOR]->(s)""", Map.of("id", id, "stepId", stepId)).consume();
				}
				return new Stored(id, testId, true);
			});
		}
	}

	/** What can be checked without reading the run. Lists every failing field. */
	private static void checkBody(String runId, int stepIndex, JsonNode body) {
		if (!body.isObject()) {
			throw new InvalidRequestException("$", "A step result must be a JSON object");
		}
		List<FieldError> errors = new ArrayList<>();
		if (!runId.equals(body.path("runId").asString(""))) {
			errors.add(new FieldError("$.runId", "runId must be the run in the path: " + runId));
		}
		JsonNode index = body.path("stepIndex");
		if (!index.isIntegralNumber() || !index.canConvertToInt() || index.intValue() != stepIndex) {
			errors.add(new FieldError("$.stepIndex", "stepIndex must be the step in the path: " + stepIndex));
		}
		String status = body.path("status").asString("");
		if (status.equals(REPAIR_PROPOSED)) {
			errors.add(new FieldError("$.status", "repairProposed results are not accepted yet (#51, #74)"));
		}
		else if (!RESULT_STATUSES.contains(status)) {
			errors.add(new FieldError("$.status", "A step result is passed, failed or notRun, not '" + status + "'"));
		}
		JsonNode stepId = body.path("stepId");
		if (!stepId.isMissingNode() && !stepId.isNull() && !stepId.isString()) {
			errors.add(new FieldError("$.stepId", "stepId must be a string or null"));
		}
		JsonNode duration = body.path("duration");
		if (!duration.isMissingNode() && !duration.isNull()
				&& (!duration.isIntegralNumber() || !duration.canConvertToLong() || duration.longValue() < 0)) {
			errors.add(new FieldError("$.duration", "duration must be a whole number of milliseconds, 0 or more"));
		}
		JsonNode message = body.path("message");
		if (!message.isMissingNode() && !message.isNull() && !message.isString()) {
			errors.add(new FieldError("$.message", "message must be a string or null"));
		}
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The step result is invalid", errors);
		}
	}

	private void checkAgainstRun(Value run, int stepIndex, String stepId) {
		int stepCount = run.get("stepCount").asInt();
		if (stepIndex < 0 || stepIndex >= stepCount) {
			throw new InvalidRequestException("$.stepIndex",
					"Step index " + stepIndex + " is outside this run's " + stepCount + " steps");
		}
		String expected = mapper.readTree(run.get("document").asString())
			.path("steps")
			.path(stepIndex)
			.path("id")
			.asString("");
		if (stepId != null && !stepId.equals(expected)) {
			throw new InvalidRequestException("$.stepId", "Step " + stepIndex + " of this run is " + expected);
		}
	}

	private static void requireSameApplication(TransactionContext tx, String testId, String appVersionId) {
		var test = tx.run("MATCH (a:Application)-[:HAS_TEST]->(:TestCase {id: $id}) RETURN a.id AS appId",
				Map.of("id", testId));
		if (!test.hasNext()) {
			throw new NotFoundException("Test not found: " + testId);
		}
		String appId = test.next().get("appId").asString();
		var version = tx.run("MATCH (a:Application)-[:HAS_VERSION]->(:AppVersion {id: $id}) RETURN a.id AS appId",
				Map.of("id", appVersionId));
		if (!version.hasNext()) {
			throw new NotFoundException("Application version not found: " + appVersionId);
		}
		if (!appId.equals(version.next().get("appId").asString())) {
			throw new InvalidRequestException("$.appVersionId",
					"Version " + appVersionId + " belongs to another application than the test");
		}
	}

	private static void requireFits(RunDetail run, String status) {
		long passed = run.results().stream().filter(r -> r.status().equals(PASSED)).count();
		long failed = run.results().stream().filter(r -> r.status().equals(FAILED)).count();
		if (status.equals(PASSED) && passed != run.stepCount()) {
			throw new ConflictException(
					"Run " + run.id() + " cannot pass: " + passed + " of " + run.stepCount() + " steps passed");
		}
		if (status.equals(FAILED) && failed == 0) {
			throw new ConflictException("Run " + run.id() + " cannot fail: no step failed");
		}
	}

	/** The run with its test and version; 404 if there is no such run. */
	private static Record runRecord(TransactionContext tx, String runId) {
		var result = tx.run("""
				MATCH (r:Run {id: $id})-[:OF]->(t:TestCase)
				MATCH (r)-[:ON_VERSION]->(v:AppVersion)
				""" + RUN_FIELDS, Map.of("id", runId));
		if (!result.hasNext()) {
			throw new NotFoundException("Run not found: " + runId);
		}
		return result.next();
	}

	private RunDetail detail(TransactionContext tx, String runId) {
		Record r = runRecord(tx, runId);
		RunSummary run = summary(r);
		List<StepResultResponse> results = tx.run("""
				MATCH (:Run {id: $id})-[:HAS_RESULT]->(sr:StepResult)
				RETURN sr ORDER BY sr.stepIndex""", Map.of("id", runId)).list(RunService::result);
		return new RunDetail(run.id(), run.testId(), run.appVersionId(), run.status(), run.stepCount(), run.startedBy(),
				run.startedAt(), run.finishedAt(), run.duration(),
				mapper.readTree(r.get("r").get("document").asString()), results);
	}

	private static RunSummary summary(Record r) {
		Value run = r.get("r");
		return new RunSummary(run.get("id").asString(), r.get("testId").asString(), r.get("appVersionId").asString(),
				run.get("status").asString(), run.get("stepCount").asInt(),
				new UserRef(run.get("startedBy").asString(), r.get("username").asString(null)),
				instant(run.get("startedAt")), instant(run.get("finishedAt")), longOrNull(run.get("duration")));
	}

	private static RunSummary summary(RunDetail run) {
		return new RunSummary(run.id(), run.testId(), run.appVersionId(), run.status(), run.stepCount(), run.startedBy(),
				run.startedAt(), run.finishedAt(), run.duration());
	}

	private static StepResultResponse result(Record r) {
		Value result = r.get("sr");
		return new StepResultResponse(result.get("id").asString(), result.get("stepIndex").asInt(),
				result.get("stepId").asString(null), result.get("status").asString(), longOrNull(result.get("duration")),
				result.get("message").asString(null), instant(result.get("receivedAt")));
	}

	private static Instant instant(Value value) {
		return value.isNull() ? null : value.asZonedDateTime().toInstant();
	}

	private static Long longOrNull(Value value) {
		return value.isNull() ? null : Long.valueOf(value.asLong());
	}

	private static String text(JsonNode body, String field) {
		JsonNode value = body.path(field);
		return value.isString() ? value.asString() : null;
	}

	private static Long number(JsonNode body, String field) {
		JsonNode value = body.path(field);
		return value.isIntegralNumber() ? Long.valueOf(value.longValue()) : null;
	}

	/** The same content with object keys sorted, so a repeat compares equal whatever its key order. */
	private JsonNode sorted(JsonNode node) {
		if (node.isObject()) {
			ObjectNode copy = mapper.createObjectNode();
			new TreeSet<>(node.propertyNames()).forEach(name -> copy.set(name, sorted(node.get(name))));
			return copy;
		}
		if (node.isArray()) {
			ArrayNode copy = mapper.createArrayNode();
			node.forEach(item -> copy.add(sorted(item)));
			return copy;
		}
		return node;
	}

	private static String sha256(String text) {
		try {
			byte[] digest = MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
			return HexFormat.of().formatHex(digest);
		}
		catch (NoSuchAlgorithmException ex) {
			throw new IllegalStateException("SHA-256 is missing from this JVM", ex);
		}
	}

	/** `created` is false for an identical repeat, which wrote nothing. */
	public record StoredResult(String id, boolean created) {
	}

	private record Stored(String id, String testId, boolean created) {
	}

	private record Finished(RunSummary run, boolean changed) {
	}

}
