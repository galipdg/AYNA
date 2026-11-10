package com.ayna.server.runs;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
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
import com.ayna.server.error.ApiExceptions.TooLargeException;
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
 * Screenshots, the idle timeout and retention are #51's (ADR run-screenshots-and-retention).
 */
@Service
public class RunService {

	static final int HISTORY_LIMIT = 20;

	private static final String RUNNING = "running";

	private static final String PASSED = "passed";

	private static final String FAILED = "failed";

	private static final String ABORTED = "aborted";

	private static final String NOT_RUN = "notRun";

	/** Added by #74, which stores the proposal that comes with it (ADR run-screenshots-and-retention). */
	private static final String REPAIR_PROPOSED = "repairProposed";

	private static final Set<String> RUN_STATUSES = Set.of(RUNNING, PASSED, FAILED, ABORTED);

	private static final Set<String> FINISH_STATUSES = Set.of(PASSED, FAILED, ABORTED);

	private static final Set<String> RESULT_STATUSES = Set.of(PASSED, FAILED, NOT_RUN);

	/** What Neo4j reports when a uniqueness constraint refuses a write. */
	private static final String CONSTRAINT_FAILED = "Neo.ClientError.Schema.ConstraintValidationFailed";

	/** The first bytes of every PNG file. */
	private static final byte[] PNG_SIGNATURE = { (byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n' };

	/** Runs deleted per transaction by retention, so one sweep never holds a huge transaction. */
	static final int RETENTION_BATCH = 100;

	private static final String RUN_FIELDS = """
			OPTIONAL MATCH (u:User {id: r.startedBy})
			RETURN r, t.id AS testId, v.id AS appVersionId, u.username AS username""";

	private final Driver driver;

	private final TestService tests;

	private final RunEvents events;

	private final ObjectMapper mapper;

	private final ScreenshotStore screenshots;

	public RunService(Driver driver, TestService tests, RunEvents events, ObjectMapper mapper,
			ScreenshotStore screenshots) {
		this.driver = driver;
		this.tests = tests;
		this.events = events;
		this.mapper = mapper;
		this.screenshots = screenshots;
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
						  startedBy: $userId, startedAt: datetime(), lastActivityAt: datetime()})
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
							body.path("status").asString(), number(body, "durationMs"), text(body, "message")));
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
						  r.durationMs = duration.inSeconds(r.startedAt, now).milliseconds""",
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

	/**
	 * Stores the PNG of a step whose result is already stored. Safe to repeat: the same image again
	 * answers as a repeat, another image is a 409. The graph claims the image first, and the file
	 * is written after the commit; a repeat writes the file again if it is missing, so a crash
	 * between the two is healed by the client's retry.
	 */
	public ScreenshotWritten writeScreenshot(String runId, int stepIndex, byte[] png, long maxBytes) {
		if (png.length > maxBytes) {
			throw new TooLargeException("A screenshot may have at most " + maxBytes + " bytes, this one has more");
		}
		if (!isPng(png)) {
			throw new InvalidRequestException("$", "The body must be a PNG image");
		}
		String hash = sha256(png);
		String path = ScreenshotStore.relativePath(runId, stepIndex);
		Claim claim;
		try (Session session = driver.session()) {
			claim = session.executeWrite(tx -> {
				runRecord(tx, runId);
				var result = tx.run("""
						MATCH (r:Run {id: $runId})-[:HAS_RESULT]->(sr:StepResult {stepIndex: $stepIndex})
						WITH r, sr, sr.screenshotHash AS before
						SET sr.screenshotHash = coalesce(before, $hash), sr.screenshotPath = coalesce(sr.screenshotPath, $path),
						  sr.screenshotReceivedAt = coalesce(sr.screenshotReceivedAt, datetime()),
						  r.lastActivityAt = CASE WHEN before IS NULL THEN datetime() ELSE r.lastActivityAt END
						RETURN sr.id AS id, before, sr.screenshotPath AS path""",
						Map.of("runId", runId, "stepIndex", stepIndex, "hash", hash, "path", path));
				if (!result.hasNext()) {
					throw new NotFoundException(
							"Step " + stepIndex + " of run " + runId + " has no result yet; send the result first");
				}
				Record stored = result.next();
				String before = stored.get("before").asString(null);
				if (before != null && !before.equals(hash)) {
					throw new ConflictException(
							"Step " + stepIndex + " of run " + runId + " already has a different screenshot");
				}
				return new Claim(stored.get("id").asString(), stored.get("path").asString(), before == null);
			});
		}
		if (claim.created() || !screenshots.exists(claim.path())) {
			screenshots.write(claim.path(), png);
		}
		return new ScreenshotWritten(claim.stepResultId(), claim.created());
	}

	/** The PNG of a step; 404 if the run, the result or its screenshot is missing. */
	public byte[] readScreenshot(String runId, int stepIndex) {
		String path;
		try (Session session = driver.session()) {
			path = session.executeRead(tx -> {
				runRecord(tx, runId);
				var result = tx.run("""
						MATCH (:Run {id: $runId})-[:HAS_RESULT]->(sr:StepResult {stepIndex: $stepIndex})
						RETURN sr.screenshotPath AS path""", Map.of("runId", runId, "stepIndex", stepIndex));
				return result.hasNext() ? result.next().get("path").asString(null) : null;
			});
		}
		byte[] png = path == null ? null : screenshots.read(path);
		if (png == null) {
			throw new NotFoundException("Step " + stepIndex + " of run " + runId + " has no screenshot");
		}
		return png;
	}

	/**
	 * What the run's report shows (#59): the run, the names of its test, application and version,
	 * and the screenshots it has. Read in one transaction; the files are read after it. A file
	 * that has gone (retention between the two) is a step without a screenshot. 404 if no run.
	 */
	RunReport.Input reportInput(String runId) {
		record Read(RunDetail run, String testName, String applicationName, String version,
				Map<Integer, String> paths) {
		}
		Read read;
		try (Session session = driver.session()) {
			read = session.executeRead(tx -> {
				RunDetail run = detail(tx, runId);
				Record names = tx.run("""
						MATCH (r:Run {id: $id})-[:OF]->(t:TestCase)
						MATCH (r)-[:ON_VERSION]->(v:AppVersion)<-[:HAS_VERSION]-(a:Application)
						RETURN t.name AS test, a.name AS app, v.version AS version""", Map.of("id", runId)).single();
				Map<Integer, String> paths = new HashMap<>();
				tx.run("""
						MATCH (:Run {id: $id})-[:HAS_RESULT]->(sr:StepResult)
						WHERE sr.screenshotPath IS NOT NULL
						RETURN sr.stepIndex AS stepIndex, sr.screenshotPath AS path""", Map.of("id", runId))
					.forEachRemaining(r -> paths.put(r.get("stepIndex").asInt(), r.get("path").asString()));
				return new Read(run, names.get("test").asString(), names.get("app").asString(),
						names.get("version").asString(), paths);
			});
		}
		Map<Integer, byte[]> images = new HashMap<>();
		read.paths().forEach((stepIndex, path) -> {
			byte[] png = screenshots.read(path);
			if (png != null) {
				images.put(stepIndex, png);
			}
		});
		return new RunReport.Input(read.run(), read.testName(), read.applicationName(), read.version(), images);
	}

	/**
	 * Ends as `aborted` every running run with no write for `idle`: its client is gone and will
	 * not finish it (ADR run-screenshots-and-retention). Watchers get `run.finished`.
	 */
	public List<RunSummary> abortIdleRuns(Duration idle) {
		List<RunSummary> aborted;
		try (Session session = driver.session()) {
			aborted = session.executeWrite(tx -> {
				List<String> ids = tx.run("""
						MATCH (r:Run {status: $running})
						WHERE coalesce(r.lastActivityAt, r.startedAt) < datetime() - duration({milliseconds: $idleMs})
						WITH r, datetime() AS now
						SET r.status = $aborted, r.finishedAt = now, r.endedBy = 'idleTimeout',
						  r.durationMs = duration.inSeconds(r.startedAt, now).milliseconds
						RETURN r.id AS id""", Map.of("running", RUNNING, "aborted", ABORTED, "idleMs", idle.toMillis()))
					.list(r -> r.get("id").asString());
				List<RunSummary> runs = new ArrayList<>();
				for (String id : ids) {
					runs.add(summary(runRecord(tx, id)));
				}
				return runs;
			});
		}
		aborted.forEach(run -> events.publish(run.testId(), new Events.RunChanged(Events.RUN_FINISHED, run.testId(), run)));
		return aborted;
	}

	/**
	 * Keeps the newest `keep` runs of the whole server, by start time, and deletes the older ones
	 * that have ended, with their results and screenshots (NFR-28, NFR-40). A running run is never
	 * deleted, but it counts. Returns the deleted run ids.
	 */
	public List<String> deleteOldRuns(int keep) {
		List<String> deleted = new ArrayList<>();
		while (true) {
			List<String> batch;
			try (Session session = driver.session()) {
				batch = session.executeWrite(tx -> tx.run("""
						MATCH (r:Run)
						WITH r ORDER BY r.startedAt DESC, r.id DESC
						SKIP $keep
						WITH r WHERE r.status <> $running
						WITH r LIMIT $batch
						OPTIONAL MATCH (r)-[:HAS_RESULT]->(sr:StepResult)
						WITH r, r.id AS id, collect(sr) AS results
						FOREACH (sr IN results | DETACH DELETE sr)
						DETACH DELETE r
						RETURN id""", Map.of("keep", keep, "running", RUNNING, "batch", RETENTION_BATCH))
					.list(r -> r.get("id").asString()));
			}
			screenshots.deleteRuns(batch);
			deleted.addAll(batch);
			if (batch.size() < RETENTION_BATCH) {
				return deleted;
			}
		}
	}

	/** Which of these ids name a run that still exists. */
	public Set<String> existingRuns(Collection<String> runIds) {
		try (Session session = driver.session()) {
			return Set.copyOf(session.executeRead(tx -> tx.run("MATCH (r:Run) WHERE r.id IN $ids RETURN r.id AS id",
					Map.of("ids", List.copyOf(runIds))).list(r -> r.get("id").asString())));
		}
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
				params.put("durationMs", number(body, "durationMs"));
				params.put("message", text(body, "message"));
				params.put("hash", hash);
				params.put("body", canonical);
				tx.run("""
						MATCH (r:Run {id: $runId})
						SET r.lastActivityAt = datetime()
						CREATE (r)-[:HAS_RESULT]->(:StepResult {id: $id, runId: $runId, stepIndex: $stepIndex,
						  stepId: $stepId, status: $status, durationMs: $durationMs, message: $message,
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
		JsonNode durationMs = body.path("durationMs");
		if (!durationMs.isMissingNode() && !durationMs.isNull()
				&& (!durationMs.isIntegralNumber() || !durationMs.canConvertToLong() || durationMs.longValue() < 0)) {
			errors.add(new FieldError("$.durationMs", "durationMs must be a whole number of milliseconds, 0 or more"));
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
				run.startedAt(), run.finishedAt(), run.durationMs(),
				mapper.readTree(r.get("r").get("document").asString()), results);
	}

	private static RunSummary summary(Record r) {
		Value run = r.get("r");
		return new RunSummary(run.get("id").asString(), r.get("testId").asString(), r.get("appVersionId").asString(),
				run.get("status").asString(), run.get("stepCount").asInt(),
				new UserRef(run.get("startedBy").asString(), r.get("username").asString(null)),
				instant(run.get("startedAt")), instant(run.get("finishedAt")), longOrNull(run.get("durationMs")));
	}

	private static RunSummary summary(RunDetail run) {
		return new RunSummary(run.id(), run.testId(), run.appVersionId(), run.status(), run.stepCount(), run.startedBy(),
				run.startedAt(), run.finishedAt(), run.durationMs());
	}

	private static StepResultResponse result(Record r) {
		Value result = r.get("sr");
		int stepIndex = result.get("stepIndex").asInt();
		String screenshotUrl = result.get("screenshotPath").isNull() ? null
				: "/api/runs/" + result.get("runId").asString() + "/results/" + stepIndex + "/screenshot";
		return new StepResultResponse(result.get("id").asString(), stepIndex, result.get("stepId").asString(null),
				result.get("status").asString(), longOrNull(result.get("durationMs")), result.get("message").asString(null),
				instant(result.get("receivedAt")), screenshotUrl);
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

	private static boolean isPng(byte[] bytes) {
		if (bytes.length < PNG_SIGNATURE.length) {
			return false;
		}
		for (int i = 0; i < PNG_SIGNATURE.length; i++) {
			if (bytes[i] != PNG_SIGNATURE[i]) {
				return false;
			}
		}
		return true;
	}

	private static String sha256(String text) {
		return sha256(text.getBytes(StandardCharsets.UTF_8));
	}

	private static String sha256(byte[] bytes) {
		try {
			byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
			return HexFormat.of().formatHex(digest);
		}
		catch (NoSuchAlgorithmException ex) {
			throw new IllegalStateException("SHA-256 is missing from this JVM", ex);
		}
	}

	/** `created` is false for an identical repeat, which wrote nothing. */
	public record StoredResult(String id, boolean created) {
	}

	/** `created` is false for the same image again. */
	public record ScreenshotWritten(String stepResultId, boolean created) {
	}

	private record Stored(String id, String testId, boolean created) {
	}

	private record Finished(RunSummary run, boolean changed) {
	}

	private record Claim(String stepResultId, String path, boolean created) {
	}

}
