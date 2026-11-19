package com.ayna.server.healing;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
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
import com.ayna.server.healing.HealingDtos.CandidateElement;
import com.ayna.server.healing.HealingDtos.ProposalDetail;
import com.ayna.server.healing.HealingDtos.ProposalSummary;
import com.ayna.server.healing.HealingProposalSchema.Fraction;
import com.ayna.server.snapshots.SnapshotService;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Healing proposals (#74; ADRs `2026-10-20-approval-gated-self-healing`,
 * `2026-10-28-healing-proposal-transport` and its 0.2 extension). A proposal is created by the
 * `repairProposed` step result that carries it, in the same transaction as the result and its
 * snapshot ({@link #createFromResult}). Nothing changes the repository until a user approves a
 * candidate: the object then resolves to that element for the run's version, its identifying
 * properties take the element's values, and a Rule records the change. A proposal is decided once.
 */
@Service
public class HealingService {

	static final String PENDING = "pending";

	static final String APPROVED = "approved";

	static final String REJECTED = "rejected";

	static final Set<String> STATUSES = Set.of(PENDING, APPROVED, REJECTED);

	/** Proposals a list returns, newest first. */
	static final int LIST_LIMIT = 100;

	private static final String PROPOSAL = "$.healingProposal";

	private static final TypeReference<LinkedHashMap<String, Object>> PROPERTY_SET = new TypeReference<>() {
	};

	private final Driver driver;

	private final HealingProposalSchema schema;

	private final SnapshotService snapshots;

	private final ObjectMapper mapper;

	public HealingService(Driver driver, HealingProposalSchema schema, SnapshotService snapshots, ObjectMapper mapper) {
		this.driver = driver;
		this.schema = schema;
		this.snapshots = snapshots;
		this.mapper = mapper;
	}

	/** The run a `repairProposed` result belongs to, as the step-result write has read it. */
	public record RunContext(String runId, int stepIndex, String stepId, String appVersionId, String stepTarget) {
	}

	/**
	 * Inside the step-result write's transaction, after the StepResult `stepResultId` was created:
	 * checks the proposal against its schema, its arithmetic and the result around it, imports the
	 * snapshot (a repeat of a known snapshot id writes nothing) and creates the proposal with its
	 * `CANDIDATE` edges. Any refusal throws, so the whole write rolls back. Returns the proposal id.
	 */
	public String createFromResult(TransactionContext tx, String stepResultId, RunContext run, JsonNode body,
			String userId) {
		JsonNode proposal = body.path("healingProposal");
		JsonNode snapshot = body.path("snapshot");
		check(run, proposal, snapshot);

		Record object = requireObject(tx, run.appVersionId(), proposal.get("logicalName").asString());
		snapshots.importInto(tx, run.appVersionId(), snapshot, userId);

		String snapshotId = proposal.get("snapshotId").asString();
		List<String> order = new ArrayList<>(proposal.get("scorer").get("weights").propertyNames());
		List<Map<String, Object>> candidates = new ArrayList<>();
		for (JsonNode candidate : proposal.get("candidates")) {
			List<String> compared = order.stream().filter(candidate.get("similarities")::has).toList();
			Fraction score = Fraction.parse(candidate.get("score").asString());
			Map<String, Object> c = new HashMap<>();
			c.put("rank", candidate.get("rank").intValue());
			c.put("elementId", candidate.get("elementId").asString());
			c.put("score", score.toDouble());
			c.put("scoreExact", score.toString());
			c.put("properties", compared);
			c.put("contributions", compared.stream().map(p -> candidate.get("contributions").get(p).asString()).toList());
			c.put("similarities", compared.stream().map(p -> candidate.get("similarities").get(p).asString()).toList());
			candidates.add(c);
		}
		JsonNode scorer = proposal.get("scorer");
		JsonNode target = proposal.get("target");
		String id = UUID.randomUUID().toString();
		Map<String, Object> props = new HashMap<>();
		props.put("id", id);
		props.put("status", PENDING);
		props.put("logicalName", proposal.get("logicalName").asString());
		props.put("appVersionId", run.appVersionId());
		props.put("runId", run.runId());
		props.put("stepIndex", run.stepIndex());
		props.put("snapshotId", snapshotId);
		props.put("scorerId", scorer.get("id").asString());
		props.put("scorerFeatureVersion", text(scorer, "featureVersion"));
		props.put("targetFeatureVersion", text(target, "featureVersion"));
		props.put("targetElementId", text(target, "serverElementId"));
		props.put("weights", mapper.writeValueAsString(scorer.get("weights")));
		props.put("candidatesScored", proposal.get("candidatesScored").intValue());
		props.put("document", mapper.writeValueAsString(proposal));
		props.put("createdBy", userId);
		tx.run("""
				MATCH (sr:StepResult {id: $stepResultId}), (o:RepoObject {id: $objectId})
				CREATE (sr)-[:PROPOSED]->(p:HealingProposal)-[:FOR]->(o)
				SET p = $props, p.createdAt = datetime()
				WITH p
				UNWIND $candidates AS c
				MATCH (e:Element {snapshotId: $snapshotId, snapshotElementId: c.elementId})
				CREATE (p)-[:CANDIDATE {rank: c.rank, score: c.score, scoreExact: c.scoreExact, properties: c.properties,
				  contributions: c.contributions, similarities: c.similarities}]->(e)""",
				Map.of("stepResultId", stepResultId, "objectId", object.get("id").asString(), "props", props,
						"candidates", candidates, "snapshotId", snapshotId))
			.consume();
		return id;
	}

	/** The proposal a stored step result created, or null; answers an identical repeat of the write. */
	public String proposalOf(TransactionContext tx, String stepResultId) {
		var result = tx.run("MATCH (:StepResult {id: $id})-[:PROPOSED]->(p:HealingProposal) RETURN p.id AS id",
				Map.of("id", stepResultId));
		return result.hasNext() ? result.next().get("id").asString() : null;
	}

	/** Newest first, at most {@link #LIST_LIMIT}; `status` and `appVersionId` narrow them. */
	public List<ProposalSummary> list(String status, String appVersionId) {
		if (status != null && !STATUSES.contains(status)) {
			throw new InvalidRequestException("Unknown proposal status: " + status, List.of(new FieldError("status",
					"A proposal is " + String.join(", ", STATUSES.stream().sorted().toList()))));
		}
		Map<String, Object> params = new HashMap<>();
		params.put("status", status);
		params.put("appVersionId", appVersionId);
		params.put("limit", LIST_LIMIT);
		try (Session session = driver.session()) {
			return session.executeRead(tx -> tx.run("""
					MATCH (p:HealingProposal)
					WHERE ($status IS NULL OR p.status = $status) AND ($appVersionId IS NULL OR p.appVersionId = $appVersionId)
					OPTIONAL MATCH (p)-[:FOR]->(o:RepoObject)
					OPTIONAL MATCH (d:User {id: p.decidedBy})
					RETURN p, o.id AS objectId, d.username AS decidedByName,
					  COUNT { (p)-[:CANDIDATE]->() } AS candidateCount,
					  head([(p)-[c:CANDIDATE {rank: 1}]->() | c.scoreExact]) AS bestScore
					ORDER BY p.createdAt DESC LIMIT $limit""", params).list(r -> {
				Value p = r.get("p");
				return new ProposalSummary(p.get("id").asString(), p.get("status").asString(),
						p.get("logicalName").asString(), r.get("objectId").asString(null), p.get("appVersionId").asString(),
						p.get("runId").asString(), p.get("stepIndex").asInt(), r.get("candidateCount").asInt(),
						r.get("bestScore").asString(null), instant(p.get("createdAt")),
						user(p.get("decidedBy"), r.get("decidedByName")), instant(p.get("decidedAt")));
			}));
		}
	}

	public ProposalDetail get(String id) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> detail(tx, id));
		}
	}

	/**
	 * Approves the candidate of `rank`, in one transaction: the object resolves to its element for
	 * the proposal's version (the previous link for that version goes), every identifying property
	 * of the object's `primary` and `fallback` takes the element's value (keys the element lacks are
	 * dropped), and a Rule records old and new. 409 if the proposal was decided, the object was
	 * deleted, or the element has none of the object's primary properties.
	 */
	public ProposalDetail approve(String id, Integer rank, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				Value proposal = lockPending(tx, id);
				if (rank == null) {
					throw new InvalidRequestException("$.rank", "rank is required: 1 for the best candidate");
				}
				var candidate = tx.run("""
						MATCH (:HealingProposal {id: $id})-[:CANDIDATE {rank: $rank}]->(e:Element)
						RETURN e""", Map.of("id", id, "rank", rank));
				if (!candidate.hasNext()) {
					int count = tx.run("MATCH (:HealingProposal {id: $id})-[c:CANDIDATE]->() RETURN count(c) AS n",
							Map.of("id", id)).single().get("n").asInt();
					throw new InvalidRequestException("$.rank", "rank is between 1 and " + count + ", not " + rank);
				}
				Value element = candidate.next().get("e");
				var found = tx.run("""
						MATCH (:HealingProposal {id: $id})-[:FOR]->(o:RepoObject)
						OPTIONAL MATCH (o)-[r:RESOLVES_TO {version: $versionId}]->(old:Element)
						RETURN o, old.id AS previousElementId""",
						Map.of("id", id, "versionId", proposal.get("appVersionId").asString()));
				if (!found.hasNext()) {
					throw new ConflictException("The repository object " + proposal.get("logicalName").asString()
							+ " was deleted; there is nothing to repair");
				}
				Record object = found.next();
				Value o = object.get("o");
				String previousPrimary = o.get("primary").asString("{}");
				String previousFallback = o.get("fallback").asString("{}");
				Map<String, Object> primary = takeValues(previousPrimary, element);
				Map<String, Object> fallback = takeValues(previousFallback, element);
				if (primary.isEmpty()) {
					throw new ConflictException("The element of rank " + rank + " has none of the properties that identify "
							+ proposal.get("logicalName").asString() + "; edit the object in the repository instead");
				}
				String ruleId = UUID.randomUUID().toString();
				Map<String, Object> params = new HashMap<>();
				params.put("id", id);
				params.put("objectId", o.get("id").asString());
				params.put("elementId", element.get("id").asString());
				params.put("versionId", proposal.get("appVersionId").asString());
				params.put("previousElementId", object.get("previousElementId").asString(null));
				params.put("previousPrimary", previousPrimary);
				params.put("previousFallback", previousFallback);
				params.put("primary", mapper.writeValueAsString(primary));
				params.put("fallback", mapper.writeValueAsString(fallback));
				params.put("ruleId", ruleId);
				params.put("rank", rank);
				params.put("userId", userId);
				tx.run("""
						MATCH (o:RepoObject {id: $objectId})
						OPTIONAL MATCH (o)-[old:RESOLVES_TO {version: $versionId}]->()
						DELETE old""", params).consume();
				tx.run("""
						MATCH (p:HealingProposal {id: $id}), (o:RepoObject {id: $objectId}), (e:Element {id: $elementId})
						WITH p, o, e, datetime() AS now
						CREATE (o)-[:RESOLVES_TO {version: $versionId}]->(e)
						SET o.primary = $primary, o.fallback = $fallback, o.updatedBy = $userId, o.updatedAt = now
						CREATE (r:Rule {id: $ruleId, objectId: $objectId, appVersionId: $versionId, elementId: $elementId,
						  previousElementId: $previousElementId, previousPrimary: $previousPrimary,
						  previousFallback: $previousFallback, primary: $primary, fallback: $fallback,
						  createdBy: $userId, createdAt: now})
						CREATE (r)-[:LEARNED_FROM]->(p)
						CREATE (r)-[:FOR]->(o)
						SET p.status = 'approved', p.approvedRank = $rank, p.ruleId = $ruleId, p.decidedBy = $userId,
						  p.decidedAt = now""", params).consume();
				return detail(tx, id);
			});
		}
	}

	/** Rejects every candidate. The step stays `repairProposed` and the run failed; nothing else changes. */
	public ProposalDetail reject(String id, String userId) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				lockPending(tx, id);
				tx.run("""
						MATCH (p:HealingProposal {id: $id})
						SET p.status = 'rejected', p.decidedBy = $userId, p.decidedAt = datetime()""",
						Map.of("id", id, "userId", userId)).consume();
				return detail(tx, id);
			});
		}
	}

	/**
	 * Takes the proposal's write lock before reading its status, so of two overlapping decisions
	 * the second waits, then sees the first one's status and answers 409.
	 */
	private static Value lockPending(TransactionContext tx, String id) {
		var locked = tx.run("MATCH (p:HealingProposal {id: $id}) SET p.status = p.status RETURN p.id",
				Map.of("id", id));
		if (!locked.hasNext()) {
			throw new NotFoundException("Healing proposal not found: " + id);
		}
		locked.consume();
		Value proposal = tx.run("MATCH (p:HealingProposal {id: $id}) RETURN p", Map.of("id", id)).single().get("p");
		String status = proposal.get("status").asString();
		if (!status.equals(PENDING)) {
			throw new ConflictException("Healing proposal " + id + " was already " + status);
		}
		return proposal;
	}

	/** The keys of `json` (an object's primary or fallback), with the element's values; keys it lacks are dropped. */
	private Map<String, Object> takeValues(String json, Value element) {
		Map<String, Object> taken = new LinkedHashMap<>();
		for (String key : mapper.readValue(json, PROPERTY_SET).keySet()) {
			Value value = element.get(key);
			if (!value.isNull()) {
				taken.put(key, value.asObject());
			}
		}
		return taken;
	}

	/**
	 * What can be checked before the graph is touched, all at once and sorted by path: the
	 * document against its schema and arithmetic, then against the result that carries it.
	 */
	private void check(RunContext run, JsonNode proposal, JsonNode snapshot) {
		if (!proposal.isObject() || !snapshot.isObject()) {
			throw new IllegalStateException("the step-result check lets a repairProposed result through only with both");
		}
		List<FieldError> errors = new ArrayList<>(
				schema.validate(proposal).stream().map(e -> new FieldError(PROPOSAL + e.path().substring(1), e.message())).toList());
		if (!errors.isEmpty()) {
			throw new InvalidRequestException("The healing proposal does not match schema " + schema.version(), errors);
		}
		if (!run.runId().equals(proposal.get("runId").asString())) {
			errors.add(new FieldError(PROPOSAL + ".runId", "runId must be the result's: " + run.runId()));
		}
		if (proposal.get("stepIndex").intValue() != run.stepIndex()) {
			errors.add(new FieldError(PROPOSAL + ".stepIndex", "stepIndex must be the result's: " + run.stepIndex()));
		}
		if (!Objects.equals(text(proposal, "stepId"), run.stepId())) {
			errors.add(new FieldError(PROPOSAL + ".stepId", "stepId must be the result's: " + run.stepId()));
		}
		if (!run.appVersionId().equals(text(proposal, "appVersionId"))) {
			errors.add(new FieldError(PROPOSAL + ".appVersionId",
					"appVersionId must be the version the run plays: " + run.appVersionId()));
		}
		if (!proposal.get("logicalName").asString().equals(run.stepTarget())) {
			errors.add(new FieldError(PROPOSAL + ".logicalName", "Step " + run.stepIndex() + " of this run targets "
					+ (run.stepTarget() == null ? "no object" : run.stepTarget())));
		}
		String snapshotId = proposal.get("snapshotId").asString();
		if (!snapshotId.equals(snapshot.path("snapshotId").asString(null))) {
			errors.add(new FieldError(PROPOSAL + ".snapshotId", "snapshotId must be the carried snapshot's"));
		}
		else {
			Set<String> elementIds = new HashSet<>();
			snapshot.path("elements").forEach(e -> elementIds.add(e.path("id").asString("")));
			JsonNode candidates = proposal.get("candidates");
			for (int i = 0; i < candidates.size(); i++) {
				String elementId = candidates.get(i).get("elementId").asString();
				if (!elementIds.contains(elementId)) {
					errors.add(new FieldError(PROPOSAL + ".candidates[" + i + "].elementId",
							"Element " + elementId + " is not in snapshot " + snapshotId));
				}
			}
		}
		if (!errors.isEmpty()) {
			errors.sort(Comparator.comparing(FieldError::path));
			throw new InvalidRequestException("The healing proposal does not fit its step result", errors);
		}
	}

	private static Record requireObject(TransactionContext tx, String appVersionId, String logicalName) {
		var object = tx.run("""
				MATCH (:AppVersion {id: $versionId})<-[:HAS_VERSION]-(:Application)-[:HAS_OBJECT]->(o:RepoObject {name: $name})
				RETURN o.id AS id""", Map.of("versionId", appVersionId, "name", logicalName));
		if (!object.hasNext()) {
			throw new InvalidRequestException(PROPOSAL + ".logicalName",
					"The application has no repository object named " + logicalName);
		}
		return object.next();
	}

	private ProposalDetail detail(TransactionContext tx, String id) {
		var result = tx.run("""
				MATCH (p:HealingProposal {id: $id})
				OPTIONAL MATCH (p)-[:FOR]->(o:RepoObject)
				OPTIONAL MATCH (sr:StepResult)-[:PROPOSED]->(p)
				OPTIONAL MATCH (c:User {id: p.createdBy})
				OPTIONAL MATCH (d:User {id: p.decidedBy})
				RETURN p, o.id AS objectId, sr.id AS stepResultId, c.username AS createdByName,
				  d.username AS decidedByName,
				  [(p)-[cand:CANDIDATE]->(e:Element) | {rank: cand.rank, elementId: e.id,
				    snapshotElementId: e.snapshotElementId}] AS candidates""", Map.of("id", id));
		if (!result.hasNext()) {
			throw new NotFoundException("Healing proposal not found: " + id);
		}
		Record r = result.next();
		Value p = r.get("p");
		List<CandidateElement> candidates = new ArrayList<>(r.get("candidates")
			.asList(c -> new CandidateElement(c.get("rank").asInt(), c.get("elementId").asString(),
					c.get("snapshotElementId").asString(null))));
		candidates.sort(Comparator.comparingInt(CandidateElement::rank));
		Value approvedRank = p.get("approvedRank");
		return new ProposalDetail(p.get("id").asString(), p.get("status").asString(), p.get("logicalName").asString(),
				r.get("objectId").asString(null), p.get("appVersionId").asString(), p.get("runId").asString(),
				p.get("stepIndex").asInt(), r.get("stepResultId").asString(null),
				user(p.get("createdBy"), r.get("createdByName")), instant(p.get("createdAt")),
				user(p.get("decidedBy"), r.get("decidedByName")), instant(p.get("decidedAt")),
				approvedRank.isNull() ? null : approvedRank.asInt(), p.get("ruleId").asString(null), candidates,
				mapper.readTree(p.get("document").asString()));
	}

	private static UserRef user(Value id, Value name) {
		return id.isNull() ? null : new UserRef(id.asString(), name.asString(null));
	}

	private static Instant instant(Value value) {
		return value.isNull() ? null : value.asZonedDateTime().toInstant();
	}

	private static String text(JsonNode node, String field) {
		JsonNode value = node.path(field);
		return value.isString() ? value.asString() : null;
	}

}
