package com.ayna.server.tests;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.List;

import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ErrorResponses;
import com.ayna.server.tests.TestDtos.CreateTestRequest;
import com.ayna.server.tests.TestDtos.RenameTestRequest;
import com.ayna.server.tests.TestDtos.TestExport;
import com.ayna.server.tests.TestDtos.TestResponse;
import com.ayna.server.tests.TestDtos.TestSummary;

import tools.jackson.databind.JsonNode;

/** Tests and their steps, export and import (#39). */
@RestController
public class TestController {

	private final TestService service;

	public TestController(TestService service) {
		this.service = service;
	}

	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/apps/{appId}/tests")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<TestResponse> createTest(@PathVariable String appId, @RequestBody CreateTestRequest request) {
		TestResponse test = service.createTest(appId, required(request.name(), "name"));
		return ResponseEntity.created(URI.create("/api/tests/" + test.id())).body(test);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/apps/{appId}/tests")
	public List<TestSummary> listTests(@PathVariable String appId) {
		return service.listTests(appId);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/tests/{testId}")
	public TestResponse getTest(@PathVariable String testId) {
		return service.getTest(testId);
	}

	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PatchMapping("/api/tests/{testId}")
	public TestResponse renameTest(@PathVariable String testId, @RequestBody RenameTestRequest request) {
		return service.renameTest(testId, required(request.name(), "name"));
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@DeleteMapping("/api/tests/{testId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public ResponseEntity<Void> deleteTest(@PathVariable String testId) {
		service.deleteTest(testId);
		return ResponseEntity.noContent().build();
	}

	/** Body: a step document. Steps with an `id` keep it; the rest get new ids. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND })
	@PutMapping("/api/tests/{testId}/steps")
	public TestResponse replaceSteps(@PathVariable String testId, @RequestBody JsonNode document) {
		return service.replaceSteps(testId, document);
	}

	@ErrorResponses({ HttpStatus.NOT_FOUND })
	@GetMapping("/api/tests/{testId}/export")
	public ResponseEntity<TestExport> exportTest(@PathVariable String testId) {
		TestExport export = service.exportTest(testId);
		ContentDisposition disposition = ContentDisposition.attachment()
			.filename(export.name() + ".ayna-test.json", StandardCharsets.UTF_8)
			.build();
		return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString()).body(export);
	}

	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@PostMapping("/api/apps/{appId}/tests/import")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<TestResponse> importTest(@PathVariable String appId, @RequestBody JsonNode file) {
		TestResponse test = service.importTest(appId, file);
		return ResponseEntity.created(URI.create("/api/tests/" + test.id())).body(test);
	}

	/** Trims the value; a missing or blank value is a 400. */
	private static String required(String value, String field) {
		if (value == null || value.isBlank()) {
			throw new InvalidRequestException("$." + field, "'" + field + "' must not be blank");
		}
		return value.strip();
	}

}
