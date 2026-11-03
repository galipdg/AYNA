package com.ayna.server.snapshots;

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
import org.springframework.stereotype.Service;

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
 * the write transaction, with no constraint behind it (as #128's names), so two concurrent
 * imports of one new snapshot id can both succeed.
 */
@Service
public class SnapshotService {

	private final Driver driver;

	private final SnapshotSchema schema;

	public SnapshotService(Driver driver, SnapshotSchema schema) {
		this.driver = driver;
		this.schema = schema;
	}

	public ImportResult importSnapshot(String appId, String versionId, JsonNode document) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				if (!tx.run("MATCH (a:Application {id: $id}) RETURN a LIMIT 1", Map.of("id", appId)).hasNext()) {
					throw new NotFoundException("Application not found: " + appId);
				}
				if (!tx.run("MATCH (:Application {id: $appId})-[:HAS_VERSION]->(v:AppVersion {id: $versionId}) RETURN v",
						Map.of("appId", appId, "versionId", versionId)).hasNext()) {
					throw new NotFoundException("Version " + versionId + " not found in application " + appId);
				}
				return importInto(tx, versionId, document);
			});
		}
	}

	/**
	 * Validates and imports `document` inside the caller's transaction; the step-result write of
	 * a `repairProposed` result (#51) uses this, so its snapshot and proposal commit together.
	 */
	public ImportResult importInto(TransactionContext tx, String versionId, JsonNode document) {
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
		var existing = tx.run("""
				MATCH (v:AppVersion)-[:HAS_WINDOW]->(w:Window {snapshotId: $snapshotId})
				RETURN v.id AS versionId, w.id AS windowId, w.name AS name, w.className AS className
				LIMIT 1""", Map.of("snapshotId", snapshotId));
		if (existing.hasNext()) {
			Record row = existing.next();
			if (!row.get("versionId").asString().equals(versionId)) {
				throw new ConflictException("Snapshot " + snapshotId + " was already imported into version "
						+ row.get("versionId").asString());
			}
			int count = tx.run("MATCH (e:Element {snapshotId: $snapshotId}) RETURN count(e) AS n",
					Map.of("snapshotId", snapshotId)).single().get("n").asInt();
			return new ImportResult(new SnapshotResponse(row.get("windowId").asString(), snapshotId, versionId,
					row.get("name").asString(null), row.get("className").asString(null), count), false);
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
				"links", links, "rootId", rootId);
		tx.run("""
				MATCH (v:AppVersion {id: $versionId})
				CREATE (v)-[:HAS_WINDOW]->(w:Window)
				SET w = $window
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
		return new ImportResult(new SnapshotResponse((String) window.get("id"), snapshotId, versionId,
				(String) window.get("name"), (String) window.get("className"), entries.size()), true);
	}

	/**
	 * The Window node: what identifies the window across runs and what the Spy panel shows
	 * (#24, #25). `handle` and `processId` are session-scoped and not stored.
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
