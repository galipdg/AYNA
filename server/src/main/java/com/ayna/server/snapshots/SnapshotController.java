package com.ayna.server.snapshots;

import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.snapshots.SnapshotDtos.ImportResult;
import com.ayna.server.snapshots.SnapshotDtos.SnapshotResponse;

import tools.jackson.databind.JsonNode;

/** Window snapshot import (#15). */
@RestController
public class SnapshotController {

	private final SnapshotService service;

	public SnapshotController(SnapshotService service) {
		this.service = service;
	}

	/**
	 * Body: a snapshot document (`schemas/snapshot.schema.json`). 201 on the first import; 200
	 * with the stored window when the same snapshot id was already imported into this version.
	 */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@ApiResponse(responseCode = "201", description = "Imported")
	@ApiResponse(responseCode = "200", description = "Already imported into this version; nothing was written",
			content = @Content(schema = @Schema(implementation = SnapshotResponse.class)))
	@PostMapping("/api/apps/{appId}/versions/{versionId}/snapshots")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<SnapshotResponse> importSnapshot(@PathVariable String appId, @PathVariable String versionId,
			@RequestBody JsonNode document, @AuthenticationPrincipal AynaPrincipal me) {
		ImportResult result = service.importSnapshot(appId, versionId, document, me.userId());
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.snapshot());
	}

}
