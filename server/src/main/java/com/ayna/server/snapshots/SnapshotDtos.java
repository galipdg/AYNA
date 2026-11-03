package com.ayna.server.snapshots;

/** Response bodies of the snapshot import API. */
public final class SnapshotDtos {

	private SnapshotDtos() {
	}

	/** The imported window: `windowId` is the server's Window id, `snapshotId` the agent's. */
	public record SnapshotResponse(String windowId, String snapshotId, String appVersionId, String name,
			String className, int elementCount) {
	}

	/** `created` is false when the snapshot id was already imported into the same version. */
	public record ImportResult(SnapshotResponse snapshot, boolean created) {
	}

}
