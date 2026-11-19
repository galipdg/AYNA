package com.ayna.server.healing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/**
 * Healing proposals (#74): created by a `repairProposed` step result, listed, read, approved or
 * rejected. Built on the shared example `login-button-renamed.json` and the trial-login snapshot
 * with its three candidates added (needs Docker).
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class HealingIntegrationTest {

	static final String UNKNOWN = "00000000-0000-0000-0000-000000000000";

	static final String OLD_PRIMARY = "{\"automationId\":\"QApplication.loginWindow.loginButton\"}";

	static final String OLD_FALLBACK = "{\"name\":\"Giriş\",\"controlType\":\"Button\"}";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	StepSchema stepSchema;

	String appId;

	String versionId;

	String objectId;

	String oldElementId;

	String testId;

	List<String> stepIds;

	String runId;

	@BeforeEach
	void setUp() throws Exception {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		appId = id(mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "AYNA Trial", "technology", "PySide6")))));
		versionId = id(mvc.perform(post("/api/apps/{id}/versions", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("version", "1.1.0")))));
		var created = driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(o:RepoObject {id: randomUUID(), name: 'login.loginButton',
				  primary: $primary, fallback: $fallback})
				CREATE (o)-[:RESOLVES_TO {version: $versionId}]->(e:Element {id: randomUUID(),
				  automationId: 'QApplication.loginWindow.loginButton', name: 'Giriş', controlType: 'Button'})
				RETURN o.id AS objectId, e.id AS elementId""")
			.withParameters(Map.of("appId", appId, "versionId", versionId, "primary", OLD_PRIMARY, "fallback",
					OLD_FALLBACK))
			.execute()
			.records()
			.get(0);
		objectId = created.get("objectId").asString();
		oldElementId = created.get("elementId").asString();
		testId = id(mvc.perform(post("/api/apps/{id}/tests", appId).contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("name", "Giriş")))));
		Map<String, Object> click = Map.of("keyword", "Click", "target", "login.loginButton");
		String steps = mvc
			.perform(put("/api/tests/{id}/steps", testId).contentType(MediaType.APPLICATION_JSON)
				.content(mapper.writeValueAsString(
						Map.of("version", stepSchema.version(), "steps", List.of(click, click, click)))))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();
		stepIds = JsonPath.read(steps, "$.document.steps[*].id");
		runId = id(mvc.perform(post("/api/runs").contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(Map.of("testId", testId, "appVersionId", versionId)))));
		writeResult(passed(0)).andExpect(status().isCreated());
		writeResult(passed(1)).andExpect(status().isCreated());
	}

	// --- creating a proposal through the step-result write -------------------------------

	@Test
	void aRepairProposedResultStoresItsProposalSnapshotAndCandidates() throws Exception {
		String body = writeResult(repairProposed()).andExpect(status().isCreated())
			.andExpect(jsonPath("$.stepResultId").isString())
			.andExpect(jsonPath("$.healingProposalId").isString())
			.andReturn()
			.getResponse()
			.getContentAsString();
		String proposalId = JsonPath.read(body, "$.healingProposalId");

		assertThat(count("""
				MATCH (:Run {id: $runId})-[:HAS_RESULT]->(sr:StepResult {stepIndex: 2, status: 'repairProposed'})
				  -[:PROPOSED]->(p:HealingProposal {id: $id, status: 'pending'})-[:FOR]->(:RepoObject {id: $objectId})
				RETURN count(*) AS n""", Map.of("runId", runId, "id", proposalId, "objectId", objectId))).isEqualTo(1);
		assertThat(count("MATCH (:AppVersion {id: $v})-[:HAS_WINDOW]->(:Window {snapshotId: $s}) RETURN count(*) AS n",
				Map.of("v", versionId, "s", proposal().get("snapshotId").asString()))).isEqualTo(1);
		var candidates = driver.executableQuery("""
				MATCH (:HealingProposal {id: $id})-[c:CANDIDATE]->(e:Element)
				RETURN c.rank AS rank, c.scoreExact AS exact, c.score AS score, e.snapshotElementId AS element,
				  c.properties AS properties, c.contributions AS contributions
				ORDER BY c.rank""").withParameters(Map.of("id", proposalId)).execute().records();
		assertThat(candidates).extracting(r -> r.get("element").asString()).containsExactly("e23", "e25", "e24");
		assertThat(candidates.get(0).get("exact").asString()).isEqualTo("151/192");
		assertThat(candidates.get(0).get("score").asDouble()).isCloseTo(151.0 / 192, org.assertj.core.data.Offset.offset(1e-12));
		assertThat(candidates.get(0).get("properties").asList()).hasSameSizeAs(candidates.get(0).get("contributions").asList());
	}

	@Test
	void anIdenticalRepeatAnswersWithTheSameProposal() throws Exception {
		String first = writeResult(repairProposed()).andReturn().getResponse().getContentAsString();
		String again = writeResult(repairProposed()).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();

		assertThat((String) JsonPath.read(again, "$.healingProposalId"))
			.isEqualTo(JsonPath.read(first, "$.healingProposalId"));
		assertThat(count("MATCH (p:HealingProposal) RETURN count(p) AS n", Map.of())).isEqualTo(1);
	}

	@Test
	void anotherResultHasNoProposalId() throws Exception {
		writeResult(passed(2)).andExpect(status().isCreated()).andExpect(jsonPath("$.healingProposalId").value(nullValue()));
	}

	@Test
	void aProposalWhoseArithmeticIsWrongIsRefusedAndNothingIsStored() throws Exception {
		ObjectNode result = repairProposed();
		((ObjectNode) result.get("healingProposal").get("candidates").get(0)).put("score", "4/5");

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path", contains("$.healingProposal.candidates[0].score")))
			.andExpect(jsonPath("$.errors[0].message", containsString("[sum]")));
		assertThat(count("MATCH (sr:StepResult {stepIndex: 2}) RETURN count(sr) AS n", Map.of())).isZero();
		assertThat(count("MATCH (w:Window) RETURN count(w) AS n", Map.of())).isZero();
	}

	@Test
	void aProposalThatDoesNotMatchItsResultIsRefused() throws Exception {
		ObjectNode result = repairProposed();
		((ObjectNode) result.get("healingProposal")).put("stepIndex", 1);
		((ObjectNode) result.get("healingProposal")).put("appVersionId", UNKNOWN);

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path",
					contains("$.healingProposal.appVersionId", "$.healingProposal.stepIndex")));
	}

	@Test
	void aProposalForAnotherObjectThanTheStepsTargetIsRefused() throws Exception {
		ObjectNode result = repairProposed();
		((ObjectNode) result.get("healingProposal")).put("logicalName", "login.cancelButton");

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path", contains("$.healingProposal.logicalName")));
	}

	@Test
	void aCandidateMissingFromTheSnapshotIsRefused() throws Exception {
		ObjectNode result = repairProposed();
		ArrayNode elements = (ArrayNode) result.get("snapshot").get("elements");
		for (int i = 0; i < elements.size(); i++) {
			if (elements.get(i).get("id").asString().equals("e25")) {
				elements.remove(i);
			}
		}
		((ObjectNode) result.get("snapshot").get("capture")).put("elementCount", elements.size());

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path", contains("$.healingProposal.candidates[1].elementId")));
	}

	@Test
	void aRepairProposedResultNeedsItsProposalAndSnapshot() throws Exception {
		ObjectNode result = repairProposed();
		result.remove("snapshot");
		result.remove("healingProposal");

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path", contains("$.healingProposal", "$.snapshot")));
	}

	@Test
	void onlyARepairProposedResultMayCarryAProposal() throws Exception {
		ObjectNode result = passed(2);
		result.set("healingProposal", proposal());

		writeResult(result).andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path", contains("$.healingProposal")));
	}

	@Test
	void aRunWithARepairProposedStepFinishesAsFailed() throws Exception {
		writeResult(repairProposed());

		mvc.perform(post("/api/runs/{id}/finish", runId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"status\":\"failed\"}")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("failed"));
	}

	// --- reading ---------------------------------------------------------------------------

	@Test
	void listsProposalsByStatusAndVersion() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));

		mvc.perform(get("/api/healing/proposals").param("status", "pending"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$", hasSize(1)))
			.andExpect(jsonPath("$[0].id").value(proposalId))
			.andExpect(jsonPath("$[0].logicalName").value("login.loginButton"))
			.andExpect(jsonPath("$[0].objectId").value(objectId))
			.andExpect(jsonPath("$[0].appVersionId").value(versionId))
			.andExpect(jsonPath("$[0].runId").value(runId))
			.andExpect(jsonPath("$[0].stepIndex").value(2))
			.andExpect(jsonPath("$[0].candidateCount").value(3))
			.andExpect(jsonPath("$[0].bestScore").value("151/192"));
		mvc.perform(get("/api/healing/proposals").param("status", "approved")).andExpect(jsonPath("$", hasSize(0)));
		mvc.perform(get("/api/healing/proposals").param("appVersionId", UNKNOWN)).andExpect(jsonPath("$", hasSize(0)));
		mvc.perform(get("/api/healing/proposals").param("status", "maybe")).andExpect(status().isBadRequest());
	}

	@Test
	void readsAProposalWithItsDocumentAndServerElementIds() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));
		String e25 = elementId("e25");

		mvc.perform(get("/api/healing/proposals/{id}", proposalId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("pending"))
			.andExpect(jsonPath("$.decidedBy").value(nullValue()))
			.andExpect(jsonPath("$.approvedRank").value(nullValue()))
			.andExpect(jsonPath("$.ruleId").value(nullValue()))
			.andExpect(jsonPath("$.stepResultId").isString())
			.andExpect(jsonPath("$.candidates[*].rank", contains(1, 2, 3)))
			.andExpect(jsonPath("$.candidates[1].elementId").value(e25))
			.andExpect(jsonPath("$.candidates[1].snapshotElementId").value("e25"))
			.andExpect(jsonPath("$.document.candidates[0].score").value("151/192"))
			.andExpect(jsonPath("$.document.version").value("0.2"));
		mvc.perform(get("/api/healing/proposals/{id}", UNKNOWN)).andExpect(status().isNotFound());
	}

	// --- deciding ----------------------------------------------------------------------------

	@Test
	void approvingMovesTheObjectToTheCandidateAndLearnsARule() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));
		String e25 = elementId("e25");
		JsonNode chosen = proposal().get("candidates").get(1).get("element");

		String body = mvc.perform(post("/api/healing/proposals/{id}/approve", proposalId)
			.contentType(MediaType.APPLICATION_JSON)
			.content("{\"rank\":2}"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("approved"))
			.andExpect(jsonPath("$.approvedRank").value(2))
			.andExpect(jsonPath("$.decidedBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.decidedAt").isString())
			.andExpect(jsonPath("$.ruleId").isString())
			.andReturn()
			.getResponse()
			.getContentAsString();
		String ruleId = JsonPath.read(body, "$.ruleId");

		var resolves = driver.executableQuery("""
				MATCH (:RepoObject {id: $id})-[r:RESOLVES_TO {version: $v}]->(e:Element) RETURN e.id AS e""")
			.withParameters(Map.of("id", objectId, "v", versionId))
			.execute()
			.records();
		assertThat(resolves).extracting(r -> r.get("e").asString()).containsExactly(e25);

		var object = driver.executableQuery("MATCH (o:RepoObject {id: $id}) RETURN o")
			.withParameters(Map.of("id", objectId))
			.execute()
			.records()
			.get(0)
			.get("o");
		JsonNode primary = mapper.readTree(object.get("primary").asString());
		JsonNode fallback = mapper.readTree(object.get("fallback").asString());
		assertThat(primary.propertyNames()).containsExactly("automationId");
		assertThat(primary.get("automationId").asString()).isEqualTo(chosen.get("automationId").asString());
		assertThat(fallback.propertyNames()).containsExactly("name", "controlType");
		assertThat(fallback.get("name").asString()).isEqualTo(chosen.get("name").asString());
		assertThat(object.get("updatedBy").asString()).isEqualTo(SignedIn.TESTER.userId());

		var rule = driver.executableQuery("""
				MATCH (r:Rule {id: $ruleId})-[:LEARNED_FROM]->(:HealingProposal {id: $p})
				MATCH (r)-[:FOR]->(:RepoObject {id: $o})
				RETURN r""").withParameters(Map.of("ruleId", ruleId, "p", proposalId, "o", objectId))
			.execute()
			.records();
		assertThat(rule).hasSize(1);
		var r = rule.get(0).get("r");
		assertThat(r.get("appVersionId").asString()).isEqualTo(versionId);
		assertThat(r.get("elementId").asString()).isEqualTo(e25);
		assertThat(r.get("previousElementId").asString()).isEqualTo(oldElementId);
		assertThat(mapper.readTree(r.get("previousPrimary").asString())).isEqualTo(mapper.readTree(OLD_PRIMARY));
		assertThat(mapper.readTree(r.get("primary").asString())).isEqualTo(primary);
		assertThat(r.get("createdBy").asString()).isEqualTo(SignedIn.TESTER.userId());
	}

	@Test
	void rejectingChangesNothingButTheProposal() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));

		mvc.perform(post("/api/healing/proposals/{id}/reject", proposalId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.status").value("rejected"))
			.andExpect(jsonPath("$.decidedBy.id").value(SignedIn.TESTER.userId()))
			.andExpect(jsonPath("$.decidedAt").isString())
			.andExpect(jsonPath("$.ruleId").value(nullValue()));

		assertThat(count("MATCH (:StepResult {stepIndex: 2, status: 'repairProposed'}) RETURN count(*) AS n", Map.of()))
			.isEqualTo(1);
		assertThat(count("""
				MATCH (:RepoObject {id: $o})-[:RESOLVES_TO {version: $v}]->(:Element {id: $e}) RETURN count(*) AS n""",
				Map.of("o", objectId, "v", versionId, "e", oldElementId))).isEqualTo(1);
		assertThat(count("MATCH (r:Rule) RETURN count(r) AS n", Map.of())).isZero();
		var primary = driver.executableQuery("MATCH (o:RepoObject {id: $id}) RETURN o.primary AS p")
			.withParameters(Map.of("id", objectId))
			.execute()
			.records()
			.get(0)
			.get("p")
			.asString();
		assertThat(primary).isEqualTo(OLD_PRIMARY);
	}

	@Test
	void aProposalIsDecidedOnce() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));
		mvc.perform(post("/api/healing/proposals/{id}/reject", proposalId)).andExpect(status().isOk());

		mvc.perform(post("/api/healing/proposals/{id}/reject", proposalId)).andExpect(status().isConflict());
		mvc.perform(post("/api/healing/proposals/{id}/approve", proposalId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"rank\":1}")).andExpect(status().isConflict());
	}

	@Test
	void approvingChecksTheRankAndTheProposal() throws Exception {
		String proposalId = proposalId(writeResult(repairProposed()));

		mvc.perform(post("/api/healing/proposals/{id}/approve", proposalId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"rank\":4}")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors[0].path").value("$.rank"));
		mvc.perform(post("/api/healing/proposals/{id}/approve", proposalId).contentType(MediaType.APPLICATION_JSON)
			.content("{}")).andExpect(status().isBadRequest());
		mvc.perform(post("/api/healing/proposals/{id}/approve", UNKNOWN).contentType(MediaType.APPLICATION_JSON)
			.content("{\"rank\":1}")).andExpect(status().isNotFound());
	}

	// --- helpers -------------------------------------------------------------------------------

	private ResultActions writeResult(JsonNode body) throws Exception {
		return mvc.perform(put("/api/runs/{id}/results/{i}", runId, body.get("stepIndex").asInt())
			.contentType(MediaType.APPLICATION_JSON)
			.content(mapper.writeValueAsString(body)));
	}

	private ObjectNode passed(int stepIndex) {
		ObjectNode result = mapper.createObjectNode();
		result.put("runId", runId);
		result.put("stepIndex", stepIndex);
		result.put("stepId", stepIds.get(stepIndex));
		result.put("status", "passed");
		result.put("durationMs", 120);
		return result;
	}

	/** Step 2's result: the shared proposal pointed at this run, with the snapshot its candidates come from. */
	private ObjectNode repairProposed() throws Exception {
		ObjectNode result = passed(2);
		result.put("status", "repairProposed");
		result.put("category", "elementNotFound");
		result.put("message", "login.loginButton was not found; 3 candidates proposed");
		result.set("snapshot", snapshot());
		result.set("healingProposal", proposal());
		return result;
	}

	private ObjectNode proposal() throws Exception {
		ObjectNode proposal = HealingProposalSchemaTest.loginButtonRenamed();
		proposal.put("runId", runId);
		proposal.put("stepIndex", 2);
		proposal.put("stepId", stepIds.get(2));
		proposal.put("appVersionId", versionId);
		((ObjectNode) proposal.get("target")).put("serverElementId", oldElementId);
		return proposal;
	}

	/** The trial-login snapshot (same snapshot id as the proposal) with the three candidates under its root. */
	private ObjectNode snapshot() throws Exception {
		ObjectNode snapshot = (ObjectNode) HealingProposalSchemaTest.read("schemas/examples/snapshot/trial-login.json");
		ArrayNode elements = (ArrayNode) snapshot.get("elements");
		for (JsonNode candidate : HealingProposalSchemaTest.loginButtonRenamed().get("candidates")) {
			ObjectNode entry = mapper.createObjectNode();
			entry.put("id", candidate.get("elementId").asString());
			entry.put("parentId", "e0");
			entry.set("element", candidate.get("element").deepCopy());
			elements.add(entry);
		}
		((ObjectNode) snapshot.get("capture")).put("elementCount", elements.size());
		return snapshot;
	}

	private String elementId(String snapshotElementId) {
		return driver.executableQuery("MATCH (e:Element {snapshotElementId: $s}) RETURN e.id AS id")
			.withParameters(Map.of("s", snapshotElementId))
			.execute()
			.records()
			.get(0)
			.get("id")
			.asString();
	}

	private long count(String query, Map<String, Object> params) {
		return driver.executableQuery(query).withParameters(params).execute().records().get(0).get("n").asLong();
	}

	private static String proposalId(ResultActions written) throws Exception {
		return JsonPath.read(written.andReturn().getResponse().getContentAsString(), "$.healingProposalId");
	}

	private static String id(ResultActions created) throws Exception {
		return JsonPath.read(created.andReturn().getResponse().getContentAsString(), "$.id");
	}

}
