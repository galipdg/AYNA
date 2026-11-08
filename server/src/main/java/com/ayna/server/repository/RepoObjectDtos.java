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

	/**
	 * Renames the object or replaces how it is found. A missing field keeps its value;
	 * `primary` and `fallback` are replaced together (both or neither), so the two sets never
	 * share a property.
	 */
	record UpdateRepoObjectRequest(String name, Map<String, Object> primary, Map<String, Object> fallback) {
	}

	/** Where the object is found in one application version: the Element's server id and its snapshot ids. */
	record Resolution(String appVersionId, String elementId, String snapshotId, String snapshotElementId) {
	}

	/** A test with a step that targets the object. */
	record TestRef(String id, String name) {
	}

	/**
	 * `usedBy`: the tests whose steps target the object, by name. `element`: the descriptor of
	 * the Element it resolves to in the most recent capture (descriptor property → value, in the
	 * descriptor's order), the values the editor starts from.
	 */
	record RepoObjectResponse(String id, String appId, String name, Map<String, Object> primary,
			Map<String, Object> fallback, List<Resolution> resolvesTo, List<TestRef> usedBy,
			Map<String, Object> element, UserRef createdBy, Instant createdAt, UserRef updatedBy, Instant updatedAt) {
	}

	/**
	 * One row of the repository list: `testCount` tests use the object (FR-08); `controlType`
	 * and `nearestLabel` come from the most recent capture, for search and display.
	 */
	record RepoObjectSummary(String id, String name, Map<String, Object> primary, Map<String, Object> fallback,
			String controlType, String nearestLabel, int testCount, List<Resolution> resolvesTo) {
	}

}
