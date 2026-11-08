package com.ayna.server.repository;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

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
import com.ayna.server.repository.RepoObjectDtos.CreateRepoObjectRequest;
import com.ayna.server.repository.RepoObjectDtos.RepoObjectResponse;
import com.ayna.server.repository.RepoObjectDtos.Resolution;
import com.ayna.server.snapshots.SnapshotSchema;
import com.ayna.server.tests.StepSchema;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * The object repository (#25): `(Application)-[:HAS_OBJECT]->(RepoObject)`, linked to the
 * picked Element of an imported snapshot by `RESOLVES_TO {version}`. A logical name is unique
 * per application (FR-07); the check runs in the write transaction with no constraint behind
 * it, as for test names. `primary` and `fallback` are stored as JSON strings, since Neo4j
 * properties cannot hold maps (as `Step.checkpoint`).
 */
@Service
public class RepoObjectService {

	/**
	 * Descriptor properties that never identify an element (ADR `2026-10-31-element-descriptor-v0`
	 * §3, the agent's `model.NEVER_MATCH`), plus `nearestLabelSource`, which says how
	 * `nearestLabel` was found rather than what the element is.
	 */
	static final Set<String> NEVER_MATCH = Set.of("bounds", "dpi", "nativeWindowHandle", "frameworkId", "enabled",
			"offscreen", "nearestLabelSource");

	/** Reserved by the AI service for "no object fits" (`ai/API.md`, #71); never a real object. */
	static final String NO_MATCH = "none.noMatch";

	private static final TypeReference<LinkedHashMap<String, Object>> PROPERTY_SET = new TypeReference<>() {
	};

	private final Driver driver;

	private final ObjectMapper mapper;

	private final Pattern logicalName;

	/** Property name → schema of its value, in the descriptor's order. */
	private final Map<String, JsonNode> identifying = new LinkedHashMap<>();

	public RepoObjectService(Driver driver, ObjectMapper mapper, StepSchema steps, SnapshotSchema snapshots) {
		this.driver = driver;
		this.mapper = mapper;
		this.logicalName = Pattern.compile(steps.logicalNamePattern());
		for (Map.Entry<String, JsonNode> property : snapshots.elementProperties().properties()) {
			if (!NEVER_MATCH.contains(property.getKey())) {
				identifying.put(property.getKey(), property.getValue());
			}
		}
	}

	/** `userId` is the account that adds the object (FR-40). */
	public RepoObjectResponse create(String appId, CreateRepoObjectRequest request, String userId) {
		List<FieldError> errors = new ArrayList<>();
		String name = logicalName(request.name(), errors);
		String snapshotId = required(request.snapshotId(), "snapshotId", errors);
		String snapshotElementId = required(request.snapshotElementId(), "snapshotElementId", errors);
		Map<String, Object> primary = propertySet(request.primary(), "primary", Set.of(), errors);
		Map<String, Object> fallback = propertySet(request.fallback(), "fallback", primary.keySet(), errors);
		if (request.primary() == null || request.primary().isEmpty()) {
			errors.add(new FieldError("$.primary", "At least one primary property is needed to find the element"));
		}
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The repository object is not valid", errors);
		}

		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				if (!tx.run("MATCH (a:Application {id: $id}) RETURN a LIMIT 1", Map.of("id", appId)).hasNext()) {
					throw new NotFoundException("Application not found: " + appId);
				}
				var existing = tx.run("""
						MATCH (:Application {id: $appId})-[:HAS_OBJECT]->(o:RepoObject {name: $name})
						RETURN o.id AS id LIMIT 1""", Map.of("appId", appId, "name", name));
				if (existing.hasNext()) {
					throw new ConflictException("The logical name " + name + " is already used by repository object "
							+ existing.next().get("id").asString() + " in this application");
				}
				Record element = element(tx, appId, snapshotId, snapshotElementId);

				String id = UUID.randomUUID().toString();
				Map<String, Object> params = Map.of("appId", appId, "elementId", element.get("elementId").asString(),
						"versionId", element.get("versionId").asString(), "id", id, "name", name, "primary",
						mapper.writeValueAsString(primary), "fallback", mapper.writeValueAsString(fallback), "userId",
						userId);
				tx.run("""
						MATCH (a:Application {id: $appId}), (e:Element {id: $elementId})
						WITH a, e, datetime() AS now
						CREATE (a)-[:HAS_OBJECT]->(o:RepoObject {id: $id, name: $name, primary: $primary,
						  fallback: $fallback, createdBy: $userId, createdAt: now, updatedBy: $userId, updatedAt: now})
						CREATE (o)-[:RESOLVES_TO {version: $versionId}]->(e)""", params).consume();
				return response(tx, id);
			});
		}
	}

	/** The picked Element and its version; the snapshot must have been imported into this application (#15). */
	private static Record element(TransactionContext tx, String appId, String snapshotId, String snapshotElementId) {
		Record r = tx.run("""
				OPTIONAL MATCH (:Application {id: $appId})-[:HAS_VERSION]->(v:AppVersion)
				      -[:HAS_WINDOW]->(:Window {snapshotId: $snapshotId})
				OPTIONAL MATCH (e:Element {snapshotId: $snapshotId, snapshotElementId: $snapshotElementId})
				RETURN v.id AS versionId, e.id AS elementId""",
				Map.of("appId", appId, "snapshotId", snapshotId, "snapshotElementId", snapshotElementId)).single();
		if (r.get("versionId").isNull()) {
			throw new InvalidRequestException("$.snapshotId", "Snapshot " + snapshotId
					+ " is not imported into this application; import it under a version first");
		}
		if (r.get("elementId").isNull()) {
			throw new InvalidRequestException("$.snapshotElementId",
					"Snapshot " + snapshotId + " has no element " + snapshotElementId);
		}
		return r;
	}

	private RepoObjectResponse response(TransactionContext tx, String id) {
		Record r = tx.run("""
				MATCH (a:Application)-[:HAS_OBJECT]->(o:RepoObject {id: $id})
				OPTIONAL MATCH (c:User {id: o.createdBy})
				OPTIONAL MATCH (u:User {id: o.updatedBy})
				RETURN a.id AS appId, o.name AS name, o.primary AS primary, o.fallback AS fallback,
				  o.createdBy AS createdBy, c.username AS createdByName, o.createdAt AS createdAt,
				  o.updatedBy AS updatedBy, u.username AS updatedByName, o.updatedAt AS updatedAt""", Map.of("id", id))
			.single();
		List<Resolution> resolvesTo = tx.run("""
				MATCH (:RepoObject {id: $id})-[r:RESOLVES_TO]->(e:Element)
				RETURN r.version AS versionId, e.id AS elementId, e.snapshotId AS snapshotId,
				  e.snapshotElementId AS snapshotElementId
				ORDER BY versionId""", Map.of("id", id))
			.list(row -> new Resolution(row.get("versionId").asString(), row.get("elementId").asString(),
					row.get("snapshotId").asString(), row.get("snapshotElementId").asString()));
		return new RepoObjectResponse(id, r.get("appId").asString(), r.get("name").asString(),
				mapper.readValue(r.get("primary").asString(), PROPERTY_SET),
				mapper.readValue(r.get("fallback").asString(), PROPERTY_SET), resolvesTo,
				userRef(r.get("createdBy"), r.get("createdByName")), instant(r.get("createdAt")),
				userRef(r.get("updatedBy"), r.get("updatedByName")), instant(r.get("updatedAt")));
	}

	/** Trims the name; it must have the step schema's `screen.element` form and not be reserved (SC-11). */
	private String logicalName(String value, List<FieldError> errors) {
		String name = required(value, "name", errors);
		if (name == null) {
			return null;
		}
		if (!logicalName.matcher(name).matches()) {
			errors.add(new FieldError("$.name", "'" + name
					+ "' is not a logical name: use the form screen.element, e.g. login.userNameInput"));
		}
		else if (name.equals(NO_MATCH)) {
			errors.add(new FieldError("$.name", "'" + NO_MATCH + "' is reserved: the AI service uses it for \"no object fits\""));
		}
		return name;
	}

	/**
	 * Checks one property set and keeps its order. Each key must be an identifying descriptor
	 * property, its value of the descriptor's type, and not already in `taken` (the primary set,
	 * when checking the fallback set). A missing set is empty.
	 */
	private Map<String, Object> propertySet(Map<String, Object> set, String field, Set<String> taken,
			List<FieldError> errors) {
		Map<String, Object> valid = new LinkedHashMap<>();
		if (set == null) {
			return valid;
		}
		for (Map.Entry<String, Object> entry : set.entrySet()) {
			String key = entry.getKey();
			String path = "$." + field + "." + key;
			JsonNode schema = identifying.get(key);
			if (schema == null) {
				errors.add(new FieldError(path, "'" + key + "' cannot identify an element; use one of: "
						+ String.join(", ", identifying.keySet())));
			}
			else if (taken.contains(key)) {
				errors.add(new FieldError(path, "'" + key + "' is already a primary property"));
			}
			else {
				String problem = valueProblem(schema, entry.getValue());
				if (problem != null) {
					errors.add(new FieldError(path, "'" + key + "' " + problem));
				}
				else {
					valid.put(key, entry.getValue());
				}
			}
		}
		return valid;
	}

	/** Null when `value` fits the descriptor property's schema (`type`, `minLength`, `minimum`). */
	private static String valueProblem(JsonNode schema, Object value) {
		return switch (schema.path("type").asString("")) {
			case "string" -> value instanceof String s && !s.isEmpty() ? null : "must be a non-empty string";
			case "integer" -> (value instanceof Integer || value instanceof Long)
					&& ((Number) value).longValue() >= schema.path("minimum").asLong(Long.MIN_VALUE) ? null
							: "must be an integer" + (schema.has("minimum") ? " ≥ " + schema.get("minimum").asLong() : "");
			case "boolean" -> value instanceof Boolean ? null : "must be true or false";
			default -> throw new IllegalStateException("No rule for the descriptor property schema " + schema);
		};
	}

	/** Trims the value; a missing or blank value is an error and gives null. */
	private static String required(String value, String field, List<FieldError> errors) {
		if (value == null || value.isBlank()) {
			errors.add(new FieldError("$." + field, "'" + field + "' must not be blank"));
			return null;
		}
		return value.strip();
	}

	/** Null for an object written before accounts existed (#60). */
	private static UserRef userRef(Value id, Value username) {
		return id.isNull() ? null : new UserRef(id.asString(), username.isNull() ? null : username.asString());
	}

	private static Instant instant(Value value) {
		return value.isNull() ? null : value.asZonedDateTime().toInstant();
	}

}
