package com.ayna.server.snapshots;

import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import org.springframework.stereotype.Component;

import com.ayna.server.error.FieldError;
import com.ayna.server.schema.SchemaFile;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * The snapshot schema (`schemas/snapshot.schema.json`, #12) plus the rules it cannot express
 * (ADR `2026-11-01-snapshot-schema-v0`): unique element ids, one root that comes first,
 * pre-order (a parent before its children, each subtree contiguous), and `capture.elementCount`
 * equal to the number of elements. The agent's `snapshot.loads` refuses the same documents
 * (its pre-order check was tightened to contiguous subtrees in #198).
 */
@Component
public class SnapshotSchema {

	private final SchemaFile file;

	public SnapshotSchema(ObjectMapper mapper) {
		this.file = new SchemaFile(mapper, "schemas/snapshot.schema.json");
	}

	/** The one document version this schema accepts (`version` is a `const`). */
	public String version() {
		return file.version();
	}

	/** The element descriptor's properties (`$defs/element/properties`): property name → schema of its value. */
	public JsonNode elementProperties() {
		return file.node().path("$defs").path("element").path("properties");
	}

	/** One entry per violation; empty when the document is valid. Tree rules run only on a schema-valid document. */
	public List<FieldError> validate(JsonNode document) {
		List<FieldError> errors = file.validate(document);
		if (!errors.isEmpty()) {
			return errors;
		}
		List<FieldError> rules = new ArrayList<>();
		String startedAt = document.get("capture").get("startedAt").asString();
		try {
			OffsetDateTime.parse(startedAt);
		}
		catch (DateTimeParseException ex) {
			rules.add(new FieldError("$.capture.startedAt", "Not an ISO 8601 date-time with a UTC offset: " + startedAt));
		}
		JsonNode elements = document.get("elements");
		if (document.get("capture").get("elementCount").asLong() != elements.size()) {
			rules.add(new FieldError("$.capture.elementCount", "elementCount is "
					+ document.get("capture").get("elementCount").asLong() + " but elements has " + elements.size()));
		}
		treeError(elements).ifPresent(rules::add);
		return rules;
	}

	/** The first element that breaks the tree rules; later ones are not reported, since one break shifts the rest. */
	private static Optional<FieldError> treeError(JsonNode elements) {
		Set<String> seen = new HashSet<>();
		Deque<String> ancestors = new ArrayDeque<>();
		Set<String> onPath = new HashSet<>();
		for (int i = 0; i < elements.size(); i++) {
			JsonNode node = elements.get(i);
			String path = "$.elements[" + i + "]";
			String id = node.get("id").asString();
			JsonNode parent = node.get("parentId");
			if (!seen.add(id)) {
				return Optional.of(new FieldError(path + ".id", "Element id '" + id + "' appears more than once"));
			}
			if (i == 0) {
				if (!parent.isNull()) {
					return Optional.of(new FieldError(path + ".parentId",
							"The first element must be the window's root, with parentId null"));
				}
			}
			else if (parent.isNull()) {
				return Optional.of(new FieldError(path + ".parentId",
						"Only the first element may have parentId null: a snapshot has one root"));
			}
			else {
				String parentId = parent.asString();
				if (!seen.contains(parentId) || parentId.equals(id)) {
					return Optional.of(new FieldError(path + ".parentId",
							"parentId '" + parentId + "' does not name an earlier element"));
				}
				if (!onPath.contains(parentId)) {
					return Optional.of(new FieldError(path + ".parentId", "Elements are not in pre-order: the subtree of '"
							+ parentId + "' ended before this element"));
				}
				while (!ancestors.peek().equals(parentId)) {
					onPath.remove(ancestors.pop());
				}
			}
			ancestors.push(id);
			onPath.add(id);
		}
		return Optional.empty();
	}

}
