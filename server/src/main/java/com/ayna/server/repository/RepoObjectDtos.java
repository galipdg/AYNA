package com.ayna.server.repository;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import com.ayna.server.auth.UserRef;

/** Request and response bodies of the object repository API. */
final class RepoObjectDtos {

	private RepoObjectDtos() {
	}

	/**
	 * Adds the element `snapshotElementId` of an imported snapshot under the logical name `name`.
	 * `primary` and `fallback` map descriptor property → value, best first; the client suggests
	 * them from the picked element and the user may edit them before saving (FR-06).
	 */
	record CreateRepoObjectRequest(String name, String snapshotId, String snapshotElementId, Map<String, Object> primary,
			Map<String, Object> fallback) {
	}

	/** Where the object is found in one application version: the Element's server id and its snapshot ids. */
	record Resolution(String appVersionId, String elementId, String snapshotId, String snapshotElementId) {
	}

	record RepoObjectResponse(String id, String appId, String name, Map<String, Object> primary,
			Map<String, Object> fallback, List<Resolution> resolvesTo, UserRef createdBy, Instant createdAt,
			UserRef updatedBy, Instant updatedAt) {
	}

}
