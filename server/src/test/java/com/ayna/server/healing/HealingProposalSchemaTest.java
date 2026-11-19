package com.ayna.server.healing;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

import com.ayna.server.error.FieldError;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/**
 * The server's proposal check agrees with the shared examples in
 * `schemas/examples/healing-proposal/` and with the reference arithmetic check
 * (`ai/tests/test_healing_proposal_schema.py`): every rule of `cases.json` is caught by name.
 */
class HealingProposalSchemaTest {

	static final ObjectMapper MAPPER = JsonMapper.builder().build();

	final HealingProposalSchema schema = new HealingProposalSchema(MAPPER);

	@Test
	void theExamplesAreValid() throws IOException {
		assertThat(schema.version()).isEqualTo("0.2");
		assertThat(schema.validate(loginButtonRenamed())).isEmpty();
		assertThat(schema.validate(read("schemas/examples/healing-proposal/cli-run-without-server.json"))).isEmpty();
	}

	@Test
	void everyValidCaseValidates() throws IOException {
		for (JsonNode example : cases().get("valid")) {
			assertThat(schema.validate(patched(example))).as(example.get("name").asString()).isEmpty();
		}
	}

	@Test
	void everyInvalidCaseIsRejected() throws IOException {
		for (JsonNode example : cases().get("invalid")) {
			assertThat(schema.validate(patched(example))).as(example.get("name").asString()).isNotEmpty();
		}
	}

	@Test
	void everyArithmeticCaseIsCaughtByItsRule() throws IOException {
		for (JsonNode example : cases().get("arithmetic")) {
			String rule = example.get("rule").asString();
			List<FieldError> errors = schema.validate(patched(example));
			assertThat(errors).as(example.get("name").asString())
				.extracting(FieldError::message)
				.anySatisfy(message -> assertThat(message).startsWith("[" + rule + "]"));
		}
	}

	static ObjectNode loginButtonRenamed() throws IOException {
		return (ObjectNode) read("schemas/examples/healing-proposal/login-button-renamed.json");
	}

	static JsonNode cases() throws IOException {
		return read("schemas/examples/healing-proposal/cases.json");
	}

	/** `base` with the case's RFC 6902 patch applied: add, remove, replace, copy and move. */
	static JsonNode patched(JsonNode example) throws IOException {
		JsonNode document = loginButtonRenamed();
		for (JsonNode operation : example.get("patch")) {
			String op = operation.get("op").asString();
			JsonNode value = operation.get("value");
			if (op.equals("move") || op.equals("copy")) {
				String from = operation.get("from").asString();
				value = document.at(from).deepCopy();
				if (op.equals("move")) {
					apply(document, "remove", from, null);
				}
				op = "add";
			}
			apply(document, op, operation.get("path").asString(), value);
		}
		return document;
	}

	private static void apply(JsonNode document, String op, String path, JsonNode value) {
		int slash = path.lastIndexOf('/');
		JsonNode parent = document.at(path.substring(0, slash));
		String key = path.substring(slash + 1).replace("~1", "/").replace("~0", "~");
		if (parent instanceof ObjectNode object) {
			switch (op) {
				case "add", "replace" -> object.set(key, value.deepCopy());
				case "remove" -> object.remove(key);
				default -> throw new IllegalArgumentException("unsupported op " + op);
			}
		}
		else if (parent instanceof ArrayNode array) {
			switch (op) {
				case "add" -> {
					if (key.equals("-")) {
						array.add(value.deepCopy());
					}
					else {
						array.insert(Integer.parseInt(key), value.deepCopy());
					}
				}
				case "replace" -> array.set(Integer.parseInt(key), value.deepCopy());
				case "remove" -> array.remove(Integer.parseInt(key));
				default -> throw new IllegalArgumentException("unsupported op " + op);
			}
		}
		else {
			throw new IllegalArgumentException("no container at " + path);
		}
	}

	static JsonNode read(String path) throws IOException {
		try (InputStream in = new ClassPathResource(path).getInputStream()) {
			return MAPPER.readTree(in);
		}
	}

}
