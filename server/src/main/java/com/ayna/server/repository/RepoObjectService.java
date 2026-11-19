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
import com.ayna.server.repository.RepoObjectDtos.RepoObjectSummary;
import com.ayna.server.repository.RepoObjectDtos.Resolution;
import com.ayna.server.repository.RepoObjectDtos.TestRef;
import com.ayna.server.repository.RepoObjectDtos.UpdateRepoObjectRequest;
import com.ayna.server.snapshots.SnapshotSchema;
import com.ayna.server.tests.StepSchema;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * The object repository (#25): `(Application)-[:HAS_OBJECT]->(RepoObject)`, linked to the
 * picked Element of an imported snapshot by `RESOLVES_TO {version}`; steps point at an object
 * by `TARGETS`, so a rename keeps them working (FR-08). A logical name is unique
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

	/** Every descriptor property, in the descriptor's order: the order of `element` in a response. */
	private final List<String> descriptor = new ArrayList<>();

	public RepoObjectService(Driver driver, ObjectMapper mapper, StepSchema steps, SnapshotSchema snapshots) {
		this.driver = driver;
		this.mapper = mapper;
		this.logicalName = Pattern.compile(steps.logicalNamePattern());
		for (Map.Entry<String, JsonNode> property : snapshots.elementProperties().properties()) {
			descriptor.add(property.getKey());
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
		requirePrimary(request.primary(), errors);
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

	/** The application's objects by name, each with how many tests use it (FR-08). */
	public List<RepoObjectSummary> list(String appId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				if (!tx.run("MATCH (a:Application {id: $id}) RETURN a LIMIT 1", Map.of("id", appId)).hasNext()) {
					throw new NotFoundException("Application not found: " + appId);
				}
				return tx.run("""
						MATCH (:Application {id: $appId})-[:HAS_OBJECT]->(o:RepoObject)
						CALL (o) {
						  OPTIONAL MATCH (o)-[:RESOLVES_TO]->(e:Element)
						  OPTIONAL MATCH (w:Window {snapshotId: e.snapshotId})
						  RETURN e ORDER BY w.capturedAt DESC LIMIT 1
						}
						RETURN o.id AS id, o.name AS name, o.primary AS primary, o.fallback AS fallback,
						  e.controlType AS controlType, e.nearestLabel AS nearestLabel,
						  """ + GridColumns.CHILDREN + """
						  AS children,
						  COUNT { MATCH (o)<-[:TARGETS]-(:Step)<-[:HAS_STEP]-(t:TestCase) RETURN DISTINCT t } AS testCount,
						  COLLECT { MATCH (o)-[r:RESOLVES_TO]->(x:Element)
						    RETURN {versionId: r.version, elementId: x.id, snapshotId: x.snapshotId,
						      snapshotElementId: x.snapshotElementId} AS resolution
						    ORDER BY resolution.versionId } AS resolvesTo
						ORDER BY name""", Map.of("appId", appId))
					.list(r -> new RepoObjectSummary(r.get("id").asString(), r.get("name").asString(),
							mapper.readValue(r.get("primary").asString(), PROPERTY_SET),
							mapper.readValue(r.get("fallback").asString(), PROPERTY_SET), text(r.get("controlType")),
							text(r.get("nearestLabel")), GridColumns.of(text(r.get("controlType")), r.get("children")), r.get("testCount").asInt(),
							r.get("resolvesTo").asList(RepoObjectService::resolution)));
			});
		}
	}

	public RepoObjectResponse get(String id) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				appOf(tx, id);
				return response(tx, id);
			});
		}
	}

	/**
	 * Renames the object and/or replaces its property sets; `userId` is the account that changes
	 * it (FR-40). The same checks as {@link #create}; 409 when another object of the application
	 * has the name. A request that changes nothing writes nothing.
	 */
	public RepoObjectResponse update(String id, UpdateRepoObjectRequest request, String userId) {
		List<FieldError> errors = new ArrayList<>();
		String name = request.name() == null ? null : logicalName(request.name(), errors);
		Map<String, Object> primary = null;
		Map<String, Object> fallback = null;
		if ((request.primary() == null) != (request.fallback() == null)) {
			String missing = request.primary() == null ? "primary" : "fallback";
			errors.add(new FieldError("$." + missing,
					"'primary' and 'fallback' are replaced together; send both (an empty fallback is {})"));
		}
		else if (request.primary() != null) {
			primary = propertySet(request.primary(), "primary", Set.of(), errors);
			fallback = propertySet(request.fallback(), "fallback", primary.keySet(), errors);
			requirePrimary(request.primary(), errors);
		}
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The repository object is not valid", errors);
		}

		Map<String, Object> changes = new LinkedHashMap<>();
		if (name != null) {
			changes.put("name", name);
		}
		if (primary != null) {
			changes.put("primary", mapper.writeValueAsString(primary));
			changes.put("fallback", mapper.writeValueAsString(fallback));
		}
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				String appId = appOf(tx, id);
				if (changes.isEmpty()) {
					return response(tx, id);
				}
				if (name != null) {
					var existing = tx.run("""
							MATCH (:Application {id: $appId})-[:HAS_OBJECT]->(o:RepoObject {name: $name})
							WHERE o.id <> $id
							RETURN o.id AS id LIMIT 1""", Map.of("appId", appId, "name", name, "id", id));
					if (existing.hasNext()) {
						throw new ConflictException("The logical name " + name + " is already used by repository object "
								+ existing.next().get("id").asString() + " in this application");
					}
				}
				tx.run("""
						MATCH (o:RepoObject {id: $id})
						SET o += $changes, o.updatedBy = $userId, o.updatedAt = datetime()""",
						Map.of("id", id, "changes", changes, "userId", userId))
					.consume();
				return response(tx, id);
			});
		}
	}

	/**
	 * Deletes the object and its `RESOLVES_TO` links; the captured Elements stay. 409 while a
	 * step targets it, naming the tests (FR-09): deleting it would break them.
	 */
	public void delete(String id) {
		try (Session session = driver.session()) {
			session.executeWriteWithoutResult(tx -> {
				appOf(tx, id);
				List<TestRef> usedBy = usedBy(tx, id);
				if (!usedBy.isEmpty()) {
					String name = tx.run("MATCH (o:RepoObject {id: $id}) RETURN o.name AS name", Map.of("id", id))
						.single()
						.get("name")
						.asString();
					throw new ConflictException(name + " is used by " + usedBy.size()
							+ (usedBy.size() == 1 ? " test: " : " tests: ")
							+ String.join(", ", usedBy.stream().map(TestRef::name).toList())
							+ ". Change those steps first");
				}
				tx.run("MATCH (o:RepoObject {id: $id}) DETACH DELETE o", Map.of("id", id)).consume();
			});
		}
	}

	/** The id of the object's application; 404 when there is no such object. */
	private static String appOf(TransactionContext tx, String id) {
		var r = tx.run("MATCH (a:Application)-[:HAS_OBJECT]->(:RepoObject {id: $id}) RETURN a.id AS appId",
				Map.of("id", id));
		if (!r.hasNext()) {
			throw new NotFoundException("Repository object not found: " + id);
		}
		return r.next().get("appId").asString();
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
		Latest latest = latestElement(tx, id);
		return new RepoObjectResponse(id, r.get("appId").asString(), r.get("name").asString(),
				mapper.readValue(r.get("primary").asString(), PROPERTY_SET),
				mapper.readValue(r.get("fallback").asString(), PROPERTY_SET), resolutions(tx, id), usedBy(tx, id),
				latest.element(), latest.columns(), userRef(r.get("createdBy"), r.get("createdByName")), instant(r.get("createdAt")),
				userRef(r.get("updatedBy"), r.get("updatedByName")), instant(r.get("updatedAt")));
	}

	private static List<Resolution> resolutions(TransactionContext tx, String id) {
		return tx.run("""
				MATCH (:RepoObject {id: $id})-[r:RESOLVES_TO]->(e:Element)
				RETURN {versionId: r.version, elementId: e.id, snapshotId: e.snapshotId,
				  snapshotElementId: e.snapshotElementId} AS resolution
				ORDER BY resolution.versionId""", Map.of("id", id))
			.list(row -> resolution(row.get("resolution")));
	}

	private static Resolution resolution(Value row) {
		return new Resolution(row.get("versionId").asString(), row.get("elementId").asString(),
				row.get("snapshotId").asString(), row.get("snapshotElementId").asString());
	}

	private static List<TestRef> usedBy(TransactionContext tx, String id) {
		return tx.run("""
				MATCH (:RepoObject {id: $id})<-[:TARGETS]-(:Step)<-[:HAS_STEP]-(t:TestCase)
				RETURN DISTINCT t.id AS id, t.name AS name
				ORDER BY name""", Map.of("id", id))
			.list(row -> new TestRef(row.get("id").asString(), row.get("name").asString()));
	}

	/** The Element an object resolves to in the most recent capture: its descriptor and its grid columns. */
	private record Latest(Map<String, Object> element, List<String> columns) {
	}

	/** The descriptor and columns of the Element in the most recent capture; both empty if none. */
	private Latest latestElement(TransactionContext tx, String id) {
		var rows = tx.run("""
				MATCH (:RepoObject {id: $id})-[:RESOLVES_TO]->(e:Element)
				OPTIONAL MATCH (w:Window {snapshotId: e.snapshotId})
				WITH e ORDER BY w.capturedAt DESC LIMIT 1
				RETURN properties(e) AS props, """ + GridColumns.CHILDREN + " AS children", Map.of("id", id)).list();
		Map<String, Object> element = new LinkedHashMap<>();
		if (rows.isEmpty()) {
			return new Latest(element, List.of());
		}
		Map<String, Object> props = rows.get(0).get("props").asMap();
		for (String property : descriptor) {
			if (props.containsKey(property)) {
				element.put(property, props.get(property));
			}
		}
		return new Latest(element, GridColumns.of((String) props.get("controlType"), rows.get(0).get("children")));
	}

	private static String text(Value value) {
		return value.isNull() ? null : value.asString();
	}

	private static void requirePrimary(Map<String, Object> primary, List<FieldError> errors) {
		if (primary == null || primary.isEmpty()) {
			errors.add(new FieldError("$.primary", "At least one primary property is needed to find the element"));
		}
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
