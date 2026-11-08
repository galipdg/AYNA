package com.ayna.server.repository;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.repository.RepoObjectDtos.CreateRepoObjectRequest;
import com.ayna.server.repository.RepoObjectDtos.RepoObjectResponse;

/** The object repository of an application (#25). */
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

}
