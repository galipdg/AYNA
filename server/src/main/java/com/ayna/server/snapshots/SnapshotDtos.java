package com.ayna.server.snapshots;

import java.time.Instant;

import com.ayna.server.auth.UserRef;

/** Response bodies of the snapshot import API. */
public final class SnapshotDtos {

	private SnapshotDtos() {
	}

	/**
	 * The imported window: `windowId` is the server's Window id, `snapshotId` the agent's;
	 * `createdBy` and `createdAt` say who imported it first, and when.
	 */
	public record SnapshotResponse(String windowId, String snapshotId, String appVersionId, String name,
			String className, int elementCount, UserRef createdBy, Instant createdAt) {
	}

	/** `created` is false when the snapshot id was already imported into the same version. */
	public record ImportResult(SnapshotResponse snapshot, boolean created) {
	}

}
