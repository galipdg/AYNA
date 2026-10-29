package com.ayna.server.tests;

import tools.jackson.databind.JsonNode;

/** Request and response bodies of the tests API. */
final class TestDtos {

	/** `format` of an exported test file. */
	static final String EXPORT_FORMAT = "ayna-test";

	private TestDtos() {
	}

	record CreateTestRequest(String name) {
	}

	record RenameTestRequest(String name) {
	}

	record TestSummary(String id, String name, int stepCount) {
	}

	/** `document` is a step document (`schemas/step.schema.json`) whose steps carry their ids. */
	record TestResponse(String id, String appId, String name, JsonNode document) {
	}

	/** An exported test: no ids, so importing it creates a new test with new steps. */
	record TestExport(String format, String name, JsonNode document) {
	}

}
