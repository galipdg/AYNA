package com.ayna.server.tests;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionContext;
import org.neo4j.driver.Value;
import org.springframework.stereotype.Service;

import com.ayna.server.auth.UserRef;
import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.NotFoundException;
import com.ayna.server.error.FieldError;
import com.ayna.server.runs.ScreenshotStore;
import com.ayna.server.tests.TestDtos.TestExport;
import com.ayna.server.tests.TestDtos.TestResponse;
import com.ayna.server.tests.TestDtos.TestSummary;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/**
 * Tests and their steps (#39). A test belongs to an application
 * (`(Application)-[:HAS_TEST]->(TestCase)`); its steps hang off it in order
 * (`HAS_STEP {order}`), and each step points at its repository object (`TARGETS`) instead of
 * storing the logical name, so renaming an object does not touch steps. Every write of the
 * step list is validated against the step schema and runs in one transaction.
 */
@Service
public class TestService {

	private final Driver driver;

	private final StepSchema schema;

	private final ObjectMapper mapper;

	private final ScreenshotStore screenshots;

	public TestService(Driver driver, StepSchema schema, ObjectMapper mapper, ScreenshotStore screenshots) {
		this.driver = driver;
		this.schema = schema;
		this.mapper = mapper;
		this.screenshots = screenshots;
	}

	/** `userId` is the account that makes the change (#60); every write stores it. */
	public TestResponse createTest(String appId, String name, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				String id = create(tx, appId, name, userId);
				return response(tx, id);
			});
		}
	}

	/** Tests of one application, sorted by name. */
	public List<TestSummary> listTests(String appId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				requireApp(tx, appId);
				return tx.run("""
						MATCH (:Application {id: $appId})-[:HAS_TEST]->(t:TestCase)
						OPTIONAL MATCH (t)-[:HAS_STEP]->(s:Step)
						RETURN t.id AS id, t.name AS name, count(s) AS stepCount
						ORDER BY name""", Map.of("appId", appId))
					.list(r -> new TestSummary(r.get("id").asString(), r.get("name").asString(),
							r.get("stepCount").asInt()));
			});
		}
	}

	public TestResponse getTest(String testId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> response(tx, testId));
		}
	}

	public TestResponse renameTest(String testId, String name, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				String appId = appOf(tx, testId);
				requireUniqueName(tx, appId, name, testId);
				tx.run("MATCH (t:TestCase {id: $id}) SET t.name = $name", Map.of("id", testId, "name", name)).consume();
				touch(tx, testId, userId);
				return response(tx, testId);
			});
		}
	}

	/**
	 * A run means nothing without its test, so its runs, their results (#44) and their screenshots
	 * (#51) go too. The files go after the commit; a folder left behind is removed by the next sweep.
	 */
	public void deleteTest(String testId) {
		List<String> runIds;
		try (Session session = driver.session()) {
			runIds = session.executeWrite(tx -> {
				appOf(tx, testId);
				List<String> ids = tx.run("""
						MATCH (:TestCase {id: $id})<-[:OF]-(r:Run)
						OPTIONAL MATCH (r)-[:HAS_RESULT]->(sr:StepResult)
						WITH r, r.id AS runId, collect(sr) AS results
						FOREACH (sr IN results | DETACH DELETE sr)
						DETACH DELETE r
						RETURN runId""", Map.of("id", testId)).list(r -> r.get("runId").asString());
				tx.run("MATCH (:TestCase {id: $id})-[:HAS_STEP]->(s:Step) DETACH DELETE s", Map.of("id", testId))
					.consume();
				tx.run("MATCH (t:TestCase {id: $id}) DETACH DELETE t", Map.of("id", testId)).consume();
				return ids;
			});
		}
		screenshots.deleteRuns(runIds);
	}

	/**
	 * Replaces the whole step list: a step with an `id` keeps its node, a step without one is
	 * new, and a step left out is deleted. Reordering is a replace with the same ids.
	 */
	public TestResponse replaceSteps(String testId, JsonNode document, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				String appId = appOf(tx, testId);
				writeSteps(tx, testId, appId, document, "$");
				touch(tx, testId, userId);
				return response(tx, testId);
			});
		}
	}

	public TestExport exportTest(String testId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				appOf(tx, testId);
				return new TestExport(TestDtos.EXPORT_FORMAT, name(tx, testId), document(tx, testId, false));
			});
		}
	}

	/** Creates a new test from an exported file; nothing is written if any part is invalid. */
	public TestResponse importTest(String appId, JsonNode file, String userId) {
		if (!file.isObject() || !TestDtos.EXPORT_FORMAT.equals(file.path("format").asString(""))) {
			throw new InvalidRequestException("$.format", "Not an AYNA test file: 'format' must be '"
					+ TestDtos.EXPORT_FORMAT + "'");
		}
		String name = file.path("name").asString("").strip();
		if (name.isEmpty()) {
			throw new InvalidRequestException("$.name", "'name' must not be blank");
		}
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				String id = create(tx, appId, name, userId);
				writeSteps(tx, id, appId, file.path("document"), "$.document");
				return response(tx, id);
			});
		}
	}

	private String create(TransactionContext tx, String appId, String name, String userId) {
		requireApp(tx, appId);
		requireUniqueName(tx, appId, name, null);
		String id = UUID.randomUUID().toString();
		tx.run("""
				MATCH (a:Application {id: $appId})
				WITH a, datetime() AS now
				CREATE (a)-[:HAS_TEST]->(:TestCase {id: $id, name: $name, createdBy: $userId, createdAt: now,
				  updatedBy: $userId, updatedAt: now})""",
				Map.of("appId", appId, "id", id, "name", name, "userId", userId))
			.consume();
		return id;
	}

	private static void touch(TransactionContext tx, String testId, String userId) {
		tx.run("MATCH (t:TestCase {id: $id}) SET t.updatedBy = $userId, t.updatedAt = datetime()",
				Map.of("id", testId, "userId", userId))
			.consume();
	}

	/** `prefix` is where the document sits in the request body, so error paths point into it. */
	private void writeSteps(TransactionContext tx, String testId, String appId, JsonNode document, String prefix) {
		if (!document.isObject()) {
			throw new InvalidRequestException(prefix, "Expected a step document {version, steps}");
		}
		List<FieldError> schemaErrors = schema.validate(document)
			.stream()
			.map(e -> new FieldError(prefix + e.path().substring(1), e.message()))
			.toList();
		if (!schemaErrors.isEmpty()) {
			throw new InvalidRequestException("The steps do not match step schema " + schema.version(), schemaErrors);
		}

		JsonNode steps = document.get("steps");
		Set<String> existing = new HashSet<>(tx.run("MATCH (:TestCase {id: $id})-[:HAS_STEP]->(s:Step) RETURN s.id AS id",
				Map.of("id", testId))
			.list(r -> r.get("id").asString()));
		Map<String, String> objects = objectIds(tx, appId, steps);

		List<FieldError> errors = new ArrayList<>();
		Set<String> seen = new HashSet<>();
		List<Map<String, Object>> rows = new ArrayList<>();
		for (int i = 0; i < steps.size(); i++) {
			JsonNode step = steps.get(i);
			String path = prefix + ".steps[" + i + "]";
			String id = step.has("id") ? step.get("id").asString() : UUID.randomUUID().toString();
			if (step.has("id") && !seen.add(id)) {
				errors.add(new FieldError(path + ".id", "Step id " + id + " appears more than once"));
			}
			else if (step.has("id") && !existing.contains(id)) {
				errors.add(new FieldError(path + ".id", "Step " + id + " is not a step of this test"));
			}
			String target = step.get("target").asString();
			String objectId = objects.get(target);
			if (objectId == null) {
				errors.add(new FieldError(path + ".target",
						"No repository object named '" + target + "' in this application"));
			}
			Map<String, Object> props = properties(step);
			props.put("id", id);
			Map<String, Object> row = new HashMap<>();
			row.put("order", i);
			row.put("objectId", objectId);
			row.put("props", props);
			rows.add(row);
		}
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The steps refer to unknown step ids or repository objects", errors);
		}

		List<String> keep = rows.stream().map(r -> (String) ((Map<?, ?>) r.get("props")).get("id")).toList();
		Map<String, Object> params = Map.of("testId", testId, "keep", keep, "rows", rows);
		tx.run("""
				MATCH (:TestCase {id: $testId})-[:HAS_STEP]->(s:Step)
				WHERE NOT s.id IN $keep
				DETACH DELETE s""", params).consume();
		tx.run("""
				MATCH (:TestCase {id: $testId})-[r:HAS_STEP]->(s:Step)
				OPTIONAL MATCH (s)-[t:TARGETS]->()
				DELETE r, t""", params).consume();
		tx.run("""
				MATCH (t:TestCase {id: $testId})
				UNWIND $rows AS row
				MATCH (o:RepoObject {id: row.objectId})
				MERGE (s:Step {id: row.props.id})
				SET s = row.props
				CREATE (t)-[:HAS_STEP {order: row.order}]->(s)
				CREATE (s)-[:TARGETS]->(o)""", params).consume();
	}

	/** Logical name → RepoObject id for the targets of `steps` that exist in the application. */
	private static Map<String, String> objectIds(TransactionContext tx, String appId, JsonNode steps) {
		Set<String> names = new HashSet<>();
		steps.forEach(step -> names.add(step.get("target").asString()));
		Map<String, String> ids = new HashMap<>();
		tx.run("""
				MATCH (:Application {id: $appId})-[:HAS_OBJECT]->(o:RepoObject)
				WHERE o.name IN $names
				RETURN o.name AS name, o.id AS id""", Map.of("appId", appId, "names", List.copyOf(names)))
			.forEachRemaining(r -> ids.put(r.get("name").asString(), r.get("id").asString()));
		return ids;
	}

	/** A step's fields as node properties: everything except `id` and `target`. */
	private Map<String, Object> properties(JsonNode step) {
		Map<String, Object> props = new HashMap<>();
		for (Map.Entry<String, JsonNode> field : step.properties()) {
			String name = field.getKey();
			JsonNode value = field.getValue();
			if (name.equals("id") || name.equals("target")) {
				continue;
			}
			if (value.isObject() || value.isArray()) {
				if (!StepSchema.JSON_FIELDS.contains(name)) {
					throw new IllegalStateException("No storage rule for the structured step field '" + name + "'");
				}
				props.put(name, mapper.writeValueAsString(value));
			}
			else if (value.isString()) {
				props.put(name, value.asString());
			}
			else if (value.isIntegralNumber()) {
				props.put(name, value.longValue());
			}
			else if (value.isBoolean()) {
				props.put(name, value.booleanValue());
			}
			else {
				throw new IllegalStateException("No storage rule for the step field '" + name + "'");
			}
		}
		return props;
	}

	/** The test's steps with their ids, read inside the caller's transaction (a run copies them, #44). */
	public JsonNode stepDocument(TransactionContext tx, String testId) {
		return document(tx, testId, true);
	}

	/** The test's steps as a step document; `withIds` is false for exports. */
	private JsonNode document(TransactionContext tx, String testId, boolean withIds) {
		ObjectNode document = mapper.createObjectNode();
		document.put("version", schema.version());
		ArrayNode steps = document.putArray("steps");
		List<String> fields = schema.stepFields();
		tx.run("""
				MATCH (:TestCase {id: $id})-[r:HAS_STEP]->(s:Step)
				OPTIONAL MATCH (s)-[:TARGETS]->(o:RepoObject)
				RETURN properties(s) AS props, o.name AS target
				ORDER BY r.order""", Map.of("id", testId)).forEachRemaining(r -> {
			Value props = r.get("props");
			ObjectNode step = steps.addObject();
			for (String field : fields) {
				if (field.equals("target")) {
					step.put("target", r.get("target").asString());
				}
				else if (field.equals("id") && !withIds) {
					continue;
				}
				else if (props.containsKey(field)) {
					step.set(field, json(field, props.get(field)));
				}
			}
		});
		return document;
	}

	private JsonNode json(String field, Value value) {
		if (StepSchema.JSON_FIELDS.contains(field)) {
			return mapper.readTree(value.asString());
		}
		return mapper.valueToTree(value.asObject());
	}

	private TestResponse response(TransactionContext tx, String testId) {
		String appId = appOf(tx, testId);
		Record r = tx.run("""
				MATCH (t:TestCase {id: $id})
				OPTIONAL MATCH (c:User {id: t.createdBy})
				OPTIONAL MATCH (u:User {id: t.updatedBy})
				RETURN t.name AS name, t.createdAt AS createdAt, t.updatedAt AS updatedAt,
				  t.createdBy AS createdBy, c.username AS createdByName,
				  t.updatedBy AS updatedBy, u.username AS updatedByName""", Map.of("id", testId)).single();
		return new TestResponse(testId, appId, r.get("name").asString(), document(tx, testId, true),
				userRef(r.get("createdBy"), r.get("createdByName")), instant(r.get("createdAt")),
				userRef(r.get("updatedBy"), r.get("updatedByName")), instant(r.get("updatedAt")));
	}

	/** Null for a test written before accounts existed (#60). */
	private static UserRef userRef(Value id, Value username) {
		return id.isNull() ? null : new UserRef(id.asString(), username.isNull() ? null : username.asString());
	}

	private static Instant instant(Value value) {
		return value.isNull() ? null : value.asZonedDateTime().toInstant();
	}

	private static String name(TransactionContext tx, String testId) {
		return tx.run("MATCH (t:TestCase {id: $id}) RETURN t.name AS name", Map.of("id", testId))
			.single()
			.get("name")
			.asString();
	}

	/** The id of the application the test belongs to; 404 if there is no such test. */
	private static String appOf(TransactionContext tx, String testId) {
		var result = tx.run("MATCH (a:Application)-[:HAS_TEST]->(:TestCase {id: $id}) RETURN a.id AS appId",
				Map.of("id", testId));
		if (!result.hasNext()) {
			throw new NotFoundException("Test not found: " + testId);
		}
		return result.next().get("appId").asString();
	}

	private static void requireApp(TransactionContext tx, String appId) {
		if (!tx.run("MATCH (a:Application {id: $id}) RETURN a LIMIT 1", Map.of("id", appId)).hasNext()) {
			throw new NotFoundException("Application not found: " + appId);
		}
	}

	/** Test names are unique per application; `self` is the test being renamed, if any. */
	private static void requireUniqueName(TransactionContext tx, String appId, String name, String self) {
		Map<String, Object> params = new HashMap<>();
		params.put("appId", appId);
		params.put("name", name);
		params.put("self", self);
		if (tx.run("""
				MATCH (:Application {id: $appId})-[:HAS_TEST]->(t:TestCase {name: $name})
				WHERE $self IS NULL OR t.id <> $self
				RETURN t LIMIT 1""", params).hasNext()) {
			throw new ConflictException("A test with this name already exists in the application: " + name);
		}
	}

}
