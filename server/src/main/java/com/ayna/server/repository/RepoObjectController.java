package com.ayna.server.repository;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.repository.RepoObjectDtos.CreateRepoObjectRequest;
import com.ayna.server.repository.RepoObjectDtos.RepoObjectResponse;
import com.ayna.server.repository.RepoObjectDtos.RepoObjectSummary;
import com.ayna.server.repository.RepoObjectDtos.UpdateRepoObjectRequest;

/** The object repository of an application: adding (#25), listing, editing and deleting (#30). */
@RestController
public class RepoObjectController {

	private final RepoObjectService service;

	public RepoObjectController(RepoObjectService service) {
		this.service = service;
	}

	/**
	 * Adds a picked element to the repository. The client first imports the element's snapshot
	 * (`POST /api/apps/{appId}/versions/{versionId}/snapshots`); the new object resolves to that
	 * element in that version. 409 when the logical name is taken in this application.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/apps/{appId}/repo-objects")
	@ResponseStatus(HttpStatus.CREATED)
	public RepoObjectResponse createRepoObject(@PathVariable String appId, @RequestBody CreateRepoObjectRequest request,
			@AuthenticationPrincipal AynaPrincipal me) {
		return service.create(appId, request, me.userId());
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/apps/{appId}/repo-objects")
	public List<RepoObjectSummary> listRepoObjects(@PathVariable String appId) {
		return service.list(appId);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/repo-objects/{objectId}")
	public RepoObjectResponse getRepoObject(@PathVariable String objectId) {
		return service.get(objectId);
	}

	/**
	 * Renames the object and/or replaces its `primary` and `fallback` sets (both together).
	 * Steps keep working after a rename (FR-08). 409 when the new name is taken.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PatchMapping("/api/repo-objects/{objectId}")
	public RepoObjectResponse updateRepoObject(@PathVariable String objectId,
			@RequestBody UpdateRepoObjectRequest request, @AuthenticationPrincipal AynaPrincipal me) {
		return service.update(objectId, request, me.userId());
	}

	/** 409 while a test step targets the object; the message names the tests (FR-09). */
	@ErrorResponses({ HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@DeleteMapping("/api/repo-objects/{objectId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public ResponseEntity<Void> deleteRepoObject(@PathVariable String objectId) {
		service.delete(objectId);
		return ResponseEntity.noContent().build();
	}

}
