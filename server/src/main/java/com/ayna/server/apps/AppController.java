package com.ayna.server.apps;

import java.net.URI;
import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.apps.AppDtos.AppResponse;
import com.ayna.server.apps.AppDtos.CreateAppRequest;
import com.ayna.server.apps.AppDtos.CreateVersionRequest;
import com.ayna.server.apps.AppDtos.VersionResponse;
import com.ayna.server.apps.AppExceptions.InvalidRequestException;

/** Applications under test and their versions (#128). */
@RestController
@RequestMapping("/api/apps")
public class AppController {

	private final AppService service;

	public AppController(AppService service) {
		this.service = service;
	}

	@PostMapping
	public ResponseEntity<AppResponse> createApp(@RequestBody CreateAppRequest request) {
		AppResponse app = service.createApp(required(request.name(), "name"),
				required(request.technology(), "technology"));
		return ResponseEntity.created(URI.create("/api/apps/" + app.id())).body(app);
	}

	@GetMapping
	public List<AppResponse> listApps() {
		return service.listApps();
	}

	@PostMapping("/{appId}/versions")
	public ResponseEntity<VersionResponse> createVersion(@PathVariable String appId,
			@RequestBody CreateVersionRequest request) {
		VersionResponse version = service.createVersion(appId, required(request.version(), "version"));
		return ResponseEntity.created(URI.create("/api/apps/" + appId + "/versions/" + version.id()))
			.body(version);
	}

	@GetMapping("/{appId}/versions")
	public List<VersionResponse> listVersions(@PathVariable String appId) {
		return service.listVersions(appId);
	}

	/** Trims the value; a missing or blank value is a 400. */
	private static String required(String value, String field) {
		if (value == null || value.isBlank()) {
			throw new InvalidRequestException("'" + field + "' must not be blank");
		}
		return value.strip();
	}

}
