package com.ayna.server.healing;

import java.util.List;

import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.healing.HealingDtos.ApproveRequest;
import com.ayna.server.healing.HealingDtos.ProposalDetail;
import com.ayna.server.healing.HealingDtos.ProposalSummary;

/**
 * Healing proposals (#74, FR-31, FR-32). They are created by the `repairProposed` step result
 * that carries them (`PUT /api/runs/{runId}/results/{stepIndex}`); here they are read and decided.
 */
@RestController
public class HealingController {

	private final HealingService service;

	public HealingController(HealingService service) {
		this.service = service;
	}

	/** Newest first, at most 100. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST })
	@GetMapping("/api/healing/proposals")
	public List<ProposalSummary> listProposals(
			@Parameter(schema = @Schema(allowableValues = { "pending", "approved", "rejected" })) @RequestParam(
					required = false) String status,
			@RequestParam(required = false) String appVersionId) {
		return service.list(status, appVersionId);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/healing/proposals/{id}")
	public ProposalDetail getProposal(@PathVariable String id) {
		return service.get(id);
	}

	/**
	 * Approves one candidate: the object resolves to its element for the run's version, takes its
	 * property values, and a Rule records the change. 409 if the proposal was already decided.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/healing/proposals/{id}/approve")
	public ProposalDetail approveProposal(@PathVariable String id, @RequestBody(required = false) ApproveRequest request,
			@AuthenticationPrincipal AynaPrincipal me) {
		if (request == null) {
			throw new InvalidRequestException("$.rank", "rank is required: 1 for the best candidate");
		}
		return service.approve(id, request.rank(), me.userId());
	}

	/** Rejects every candidate; the step stays failed. 409 if the proposal was already decided. */
	@ErrorResponses({ HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/healing/proposals/{id}/reject")
	public ProposalDetail rejectProposal(@PathVariable String id, @AuthenticationPrincipal AynaPrincipal me) {
		return service.reject(id, me.userId());
	}

}
