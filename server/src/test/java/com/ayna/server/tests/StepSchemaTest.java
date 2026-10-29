package com.ayna.server.tests;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

import com.ayna.server.tests.StepSchema.FieldError;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

/** The server's validator agrees with the shared examples in `schemas/examples/step/`. */
class StepSchemaTest {

	static final ObjectMapper MAPPER = JsonMapper.builder().build();

	final StepSchema schema = new StepSchema(MAPPER);

	@Test
	void everyValidExampleValidates() throws IOException {
		for (JsonNode example : cases().get("valid")) {
			assertThat(schema.validate(document(example))).as(example.get("name").asString()).isEmpty();
		}
		assertThat(schema.validate(read("schemas/examples/step/login-and-customer.json"))).isEmpty();
	}

	@Test
	void everyInvalidExampleIsRejected() throws IOException {
		for (JsonNode example : cases().get("invalid")) {
			assertThat(schema.validate(document(example))).as(example.get("name").asString()).isNotEmpty();
		}
	}

	@Test
	void errorsNameTheFailingField() {
		ObjectNode document = MAPPER.createObjectNode().put("version", schema.version());
		var steps = document.putArray("steps");
		steps.addObject().put("keyword", "Type").put("target", "login.userNameInput");
		steps.addObject().put("keyword", "Click").put("target", "login.loginButton").put("value", "x");
		steps.addObject().put("keyword", "Click").put("target", "Login.button").put("x", 1);

		List<FieldError> errors = schema.validate(document);

		assertThat(errors).extracting(FieldError::path)
			.containsExactly("$.steps[0].value", "$.steps[1].value", "$.steps[2].target", "$.steps[2].x");
		assertThat(errors.get(1).message()).isEqualTo("'value' is not allowed here");
		assertThat(errors).allSatisfy(e -> assertThat(e.message()).isNotBlank().isASCII());
	}

	@Test
	void versionAndFieldsComeFromTheSchemaFile() {
		assertThat(schema.version()).matches("\\d+\\.\\d+");
		assertThat(schema.stepFields()).startsWith("id", "keyword", "target");
	}

	/**
	 * Neo4j cannot store maps or lists of maps, so every structured step field needs a
	 * storage rule. A schema release that adds one fails here until `JSON_FIELDS` covers it.
	 */
	@Test
	void everyStructuredStepFieldHasAStorageRule() {
		Set<String> scalar = Set.of("string", "integer", "number", "boolean");
		JsonNode defs = schema.schemaNode().get("$defs");
		List<String> unhandled = new ArrayList<>();
		defs.get("step").get("properties").properties().forEach(field -> {
			JsonNode sub = field.getValue();
			if (sub.has("$ref")) {
				sub = defs.get(sub.get("$ref").asString().substring("#/$defs/".length()));
			}
			boolean isScalar = sub.has("enum") || scalar.contains(sub.path("type").asString(""));
			if (!isScalar && !StepSchema.JSON_FIELDS.contains(field.getKey())) {
				unhandled.add(field.getKey());
			}
		});
		assertThat(unhandled).isEmpty();
	}

	/** A case is a whole `document` or a single `step` wrapped in a document of this version. */
	private JsonNode document(JsonNode example) {
		if (example.has("document")) {
			return example.get("document");
		}
		ObjectNode document = MAPPER.createObjectNode().put("version", schema.version());
		document.putArray("steps").add(example.get("step"));
		return document;
	}

	private static JsonNode cases() throws IOException {
		return read("schemas/examples/step/cases.json");
	}

	private static JsonNode read(String path) throws IOException {
		try (InputStream in = new ClassPathResource(path).getInputStream()) {
			return MAPPER.readTree(in);
		}
	}

}
