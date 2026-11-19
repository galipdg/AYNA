package com.ayna.server.healing;

import java.time.Instant;
import java.util.List;

import com.ayna.server.auth.UserRef;

import tools.jackson.databind.JsonNode;

/** Request and response bodies of the healing proposals API (#74). */
final class HealingDtos {

	private HealingDtos() {
	}

	/** `rank` is the candidate to approve, 1 for the best. */
	record ApproveRequest(Integer rank) {
	}

	/**
	 * One proposal in a list. `bestScore` is rank 1's score as an exact fraction (`"151/192"`);
	 * convert it to a number only to draw it. `objectId` is null once the object has been deleted.
	 */
	record ProposalSummary(String id, String status, String logicalName, String objectId, String appVersionId,
			String runId, int stepIndex, int candidateCount, String bestScore, Instant createdAt, UserRef decidedBy,
			Instant decidedAt) {
	}

	/**
	 * A candidate's server Element, so a screen can outline it; scores and reasons are in
	 * `document.candidates`, by the same rank.
	 */
	record CandidateElement(int rank, String elementId, String snapshotElementId) {
	}

	/**
	 * The proposal with its decision. `document` is the healing proposal as received
	 * (`schemas/healing-proposal.schema.json`). `stepResultId` is null once retention deleted the
	 * run; the proposal stays, because it is the decision's record (FR-36, FR-40).
	 */
	record ProposalDetail(String id, String status, String logicalName, String objectId, String appVersionId,
			String runId, int stepIndex, String stepResultId, UserRef createdBy, Instant createdAt, UserRef decidedBy,
			Instant decidedAt, Integer approvedRank, String ruleId, List<CandidateElement> candidates,
			JsonNode document) {
	}

}
