package com.ayna.server.runs;

import java.time.Duration;
import java.util.List;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Keeps run storage bounded (#51, ADR run-screenshots-and-retention), once a minute by default:
 * runs whose client stopped writing end as `aborted`, runs past the retention setting are deleted
 * with their screenshots (NFR-28, NFR-40), and screenshot folders whose run is gone are removed.
 */
@Component
public class RunHousekeeping {

	private static final Logger log = LoggerFactory.getLogger(RunHousekeeping.class);

	private final RunService runs;

	private final ScreenshotStore screenshots;

	private final Duration idleTimeout;

	private final int retention;

	public RunHousekeeping(RunService runs, ScreenshotStore screenshots,
			@Value("${ayna.runs.idle-timeout:60m}") Duration idleTimeout,
			@Value("${ayna.runs.retention:1000}") int retention) {
		if (idleTimeout.isNegative() || idleTimeout.isZero()) {
			throw new IllegalArgumentException("ayna.runs.idle-timeout (AYNA_RUN_IDLE_TIMEOUT) must be positive");
		}
		if (retention < 0) {
			throw new IllegalArgumentException("ayna.runs.retention (AYNA_RUN_RETENTION) must be 0 (keep all) or more");
		}
		this.runs = runs;
		this.screenshots = screenshots;
		this.idleTimeout = idleTimeout;
		this.retention = retention;
	}

	@Scheduled(fixedDelayString = "${ayna.runs.housekeeping-interval:60s}")
	public void sweep() {
		try {
			abortIdleRuns();
			applyRetention();
			removeOrphanScreenshots();
		}
		catch (RuntimeException ex) {
			// A database that is down now may be back at the next sweep.
			log.warn("Run housekeeping failed; trying again at the next sweep", ex);
		}
	}

	void abortIdleRuns() {
		int aborted = runs.abortIdleRuns(idleTimeout).size();
		if (aborted > 0) {
			log.info("Aborted {} run(s) with no write for {}", aborted, idleTimeout);
		}
	}

	void applyRetention() {
		if (retention == 0) {
			return;
		}
		int deleted = runs.deleteOldRuns(retention).size();
		if (deleted > 0) {
			log.info("Deleted {} run(s) past the newest {}", deleted, retention);
		}
	}

	/** Folders left by a failed delete, or by an upload that finished after its run was deleted. */
	void removeOrphanScreenshots() {
		List<String> folders = screenshots.runFolders();
		if (folders.isEmpty()) {
			return;
		}
		Set<String> existing = runs.existingRuns(folders);
		screenshots.deleteRuns(folders.stream().filter(id -> !existing.contains(id)).toList());
	}

}
