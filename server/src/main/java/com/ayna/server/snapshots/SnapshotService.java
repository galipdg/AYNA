package com.ayna.server.snapshots;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionContext;
import org.neo4j.driver.exceptions.ClientException;
import org.springframework.stereotype.Service;

import com.ayna.server.auth.UserRef;
import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.NotFoundException;
import com.ayna.server.error.FieldError;
import com.ayna.server.snapshots.SnapshotDtos.ImportResult;
import com.ayna.server.snapshots.SnapshotDtos.SnapshotResponse;

import tools.jackson.databind.JsonNode;

/**
 * Imports a window snapshot (#12, `schemas/snapshot.schema.json`) under an AppVersion (#15):
 * `(AppVersion)-[:HAS_WINDOW]->(Window)-[:CONTAINS]->(root Element)`, then one Element per
 * entry linked by `CONTAINS` from its `parentId`. Every entry becomes an Element, the window's
 * own root element too, so the graph has `capture.elementCount` Elements per snapshot.
 *
 * A snapshot id is imported once (FR-04): the same id again under the same version returns the
 * stored window and writes nothing; under another version it is a conflict. The check runs in
 * the write transaction, and the `window_snapshot_id` constraint (`V0005`) refuses the second of
 * two overlapping imports of one new id, which then runs again and finds the first.
 */
@Service
public class SnapshotService {

	/** What Neo4j reports when a uniqueness constraint refuses a write. */
	private static final String CONSTRAINT_FAILED = "Neo.ClientError.Schema.ConstraintValidationFailed";

	private final Driver driver;

	private final SnapshotSchema schema;

	public SnapshotService(Driver driver, SnapshotSchema schema) {
		this.driver = driver;
		this.schema = schema;
	}

	public ImportResult importSnapshot(String appId, String versionId, JsonNode document, String userId) {
		try {
			return importOnce(appId, versionId, document, userId);
		}
		catch (ClientException ex) {
			if (!CONSTRAINT_FAILED.equals(ex.code())) {
				throw ex;
			}
			// An overlapping import of the same snapshot id committed first, so this one is now a repeat.
			return importOnce(appId, versionId, document, userId);
		}
	}

	private ImportResult importOnce(String appId, String versionId, JsonNode document, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				if (!tx.run("MATCH (a:Application {id: $id}) RETURN a LIMIT 1", Map.of("id", appId)).hasNext()) {
					throw new NotFoundException("Application not found: " + appId);
				}
				if (!tx.run("MATCH (:Application {id: $appId})-[:HAS_VERSION]->(v:AppVersion {id: $versionId}) RETURN v",
						Map.of("appId", appId, "versionId", versionId)).hasNext()) {
					throw new NotFoundException("Version " + versionId + " not found in application " + appId);
				}
				return importInto(tx, versionId, document, userId);
			});
		}
	}

	/**
	 * Validates and imports `document` inside the caller's transaction; the step-result write of
	 * a `repairProposed` result (#51) uses this, so its snapshot and proposal commit together.
	 * `userId` is the acting user, stored as the Window's `createdBy` (FR-40). When an overlapping
	 * import of the same new snapshot id commits first, the commit fails with Neo4j's
	 * `ConstraintValidationFailed`; run the whole write again and this call answers as a repeat.
	 */
	public ImportResult importInto(TransactionContext tx, String versionId, JsonNode document, String userId) {
		if (!document.isObject()) {
			throw new InvalidRequestException("$", "Expected a snapshot document {version, snapshotId, ...}");
		}
		List<FieldError> errors = schema.validate(document);
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The snapshot does not match snapshot schema " + schema.version(), errors);
		}
		if (!tx.run("MATCH (v:AppVersion {id: $id}) RETURN v", Map.of("id", versionId)).hasNext()) {
			throw new NotFoundException("Version not found: " + versionId);
		}

		String snapshotId = document.get("snapshotId").asString();
		var existing = tx.run("MATCH (v:AppVersion)-[:HAS_WINDOW]->(:Window {snapshotId: $snapshotId}) RETURN v.id AS versionId",
				Map.of("snapshotId", snapshotId));
		if (existing.hasNext()) {
			String importedInto = existing.next().get("versionId").asString();
			if (!importedInto.equals(versionId)) {
				throw new ConflictException("Snapshot " + snapshotId + " was already imported into version " + importedInto);
			}
			return new ImportResult(response(tx, snapshotId), false);
		}

		Map<String, Object> window = window(document);
		JsonNode entries = document.get("elements");
		Map<String, String> serverIds = new HashMap<>();
		List<Map<String, Object>> elements = new ArrayList<>();
		List<Map<String, Object>> links = new ArrayList<>();
		for (JsonNode entry : entries) {
			String id = UUID.randomUUID().toString();
			serverIds.put(entry.get("id").asString(), id);
			Map<String, Object> props = properties(entry.get("element"));
			props.put("id", id);
			props.put("snapshotId", snapshotId);
			props.put("snapshotElementId", entry.get("id").asString());
			elements.add(props);
			if (!entry.get("parentId").isNull()) {
				links.add(Map.of("parent", serverIds.get(entry.get("parentId").asString()), "child", id));
			}
		}
		String rootId = (String) elements.get(0).get("id");

		Map<String, Object> params = Map.of("versionId", versionId, "window", window, "elements", elements,
				"links", links, "rootId", rootId, "userId", userId);
		tx.run("""
				MATCH (v:AppVersion {id: $versionId})
				CREATE (v)-[:HAS_WINDOW]->(w:Window)
				SET w = $window, w.createdBy = $userId, w.createdAt = datetime()
				WITH w
				UNWIND $elements AS props
				CREATE (e:Element)
				SET e = props""", params).consume();
		tx.run("""
				MATCH (w:Window {id: $window.id}), (root:Element {id: $rootId})
				CREATE (w)-[:CONTAINS]->(root)""", params).consume();
		tx.run("""
				UNWIND $links AS link
				MATCH (parent:Element {id: link.parent}), (child:Element {id: link.child})
				CREATE (parent)-[:CONTAINS]->(child)""", params).consume();
		return new ImportResult(response(tx, snapshotId), true);
	}

	private static SnapshotResponse response(TransactionContext tx, String snapshotId) {
		Record r = tx.run("""
				MATCH (v:AppVersion)-[:HAS_WINDOW]->(w:Window {snapshotId: $snapshotId})
				OPTIONAL MATCH (u:User {id: w.createdBy})
				RETURN w.id AS windowId, v.id AS versionId, w.name AS name, w.className AS className,
				  COUNT { MATCH (e:Element {snapshotId: $snapshotId}) } AS elementCount,
				  w.createdBy AS createdBy, u.username AS createdByName, w.createdAt AS createdAt""",
				Map.of("snapshotId", snapshotId)).single();
		UserRef createdBy = r.get("createdBy").isNull() ? null
				: new UserRef(r.get("createdBy").asString(), r.get("createdByName").asString(null));
		Instant createdAt = r.get("createdAt").isNull() ? null : r.get("createdAt").asZonedDateTime().toInstant();
		return new SnapshotResponse(r.get("windowId").asString(), snapshotId, r.get("versionId").asString(),
				r.get("name").asString(null), r.get("className").asString(null), r.get("elementCount").asInt(), createdBy,
				createdAt);
	}

	/**
	 * The Window node: what identifies the window across runs, what the Spy panel shows (#24,
	 * #25), and the capture's evidence for measurements (#64): how long the walk took, how many
	 * property reads failed and which agent made it. `handle` and `processId` are session-scoped
	 * and not stored; `window.bounds`, `window.dpi` and `capture.budgetMs` are left out on purpose
	 * (no reader needs them; every Element keeps its own `bounds` and `dpi`).
	 */
	private static Map<String, Object> window(JsonNode document) {
		JsonNode window = document.get("window");
		JsonNode capture = document.get("capture");
		JsonNode app = document.get("app");
		Map<String, Object> props = new HashMap<>();
		props.put("id", UUID.randomUUID().toString());
		props.put("snapshotId", document.get("snapshotId").asString());
		putString(props, "name", window.get("title"));
		putString(props, "className", window.get("className"));
		props.put("capturedAt", OffsetDateTime.parse(capture.get("startedAt").asString()));
		putString(props, "featureVersion", capture.get("featureVersion"));
		props.put("captureDurationMs", capture.get("durationMs").longValue());
		if (capture.has("readErrors")) {
			props.put("readErrors", capture.get("readErrors").longValue());
		}
		putString(props, "agentVersion", capture.get("agentVersion"));
		putString(props, "exeName", app.get("exeName"));
		putString(props, "fileVersion", app.get("fileVersion"));
		return props;
	}

	private static void putString(Map<String, Object> props, String name, JsonNode value) {
		if (value != null) {
			props.put(name, value.asString());
		}
	}

	/** An element descriptor as node properties; the schema allows only scalars and the int list `bounds`. */
	private static Map<String, Object> properties(JsonNode element) {
		Map<String, Object> props = new HashMap<>();
		for (Map.Entry<String, JsonNode> field : element.properties()) {
			JsonNode value = field.getValue();
			props.put(field.getKey(), switch (value.getNodeType()) {
				case STRING -> value.asString();
				case BOOLEAN -> value.booleanValue();
				case NUMBER -> value.longValue();
				case ARRAY -> {
					List<Long> numbers = new ArrayList<>();
					value.forEach(n -> numbers.add(n.longValue()));
					yield numbers;
				}
				default -> throw new IllegalStateException("No storage rule for the element field '" + field.getKey() + "'");
			});
		}
		return props;
	}

}
