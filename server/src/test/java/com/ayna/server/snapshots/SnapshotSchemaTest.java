package com.ayna.server.snapshots;

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

/** The server's snapshot validator agrees with the shared examples in `schemas/examples/snapshot/`. */
class SnapshotSchemaTest {

	static final ObjectMapper MAPPER = JsonMapper.builder().build();

	final SnapshotSchema schema = new SnapshotSchema(MAPPER);

	@Test
	void theTrialAppSnapshotValidates() throws IOException {
		assertThat(schema.validate(trialLogin())).isEmpty();
		assertThat(schema.version()).isEqualTo("0.1");
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
	void anElementCountThatDisagreesIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		((ObjectNode) document.get("capture")).put("elementCount", 13);

		assertThat(schema.validate(document)).extracting(FieldError::path).containsExactly("$.capture.elementCount");
	}

	@Test
	void aDuplicateElementIdIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		node(document, 5).put("id", "e4");

		assertThat(schema.validate(document)).extracting(FieldError::path).containsExactly("$.elements[5].id");
	}

	@Test
	void aSecondRootIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		node(document, 3).putNull("parentId");

		assertThat(schema.validate(document)).extracting(FieldError::path).containsExactly("$.elements[3].parentId");
	}

	@Test
	void aRootThatIsNotFirstIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		node(document, 0).put("parentId", "e1");

		assertThat(schema.validate(document)).extracting(FieldError::path).containsExactly("$.elements[0].parentId");
	}

	@Test
	void aParentAfterItsChildIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		node(document, 2).put("parentId", "e9");

		List<FieldError> errors = schema.validate(document);

		assertThat(errors).extracting(FieldError::path).containsExactly("$.elements[2].parentId");
		assertThat(errors.get(0).message()).contains("does not name an earlier element");
	}

	@Test
	void anElementOutsideItsParentsSubtreeIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		ArrayNode elements = (ArrayNode) document.get("elements");
		// The last element names e1 as its parent, but e1's subtree ended long before it.
		int last = elements.size() - 1;
		String lastParent = elements.get(last).get("parentId").asString();
		assertThat(lastParent).isNotEqualTo("e1");
		node(document, last).put("parentId", "e1");

		List<FieldError> errors = schema.validate(document);

		assertThat(errors).extracting(FieldError::path).containsExactly("$.elements[" + last + "].parentId");
		assertThat(errors.get(0).message()).contains("not in pre-order");
	}

	@Test
	void aStartTimeJavaCannotParseIsRejected() throws IOException {
		ObjectNode document = trialLogin();
		((ObjectNode) document.get("capture")).put("startedAt", "2026-10-31 17:42:19+0300");

		assertThat(schema.validate(document)).extracting(FieldError::path).contains("$.capture.startedAt");
	}

	static ObjectNode trialLogin() throws IOException {
		return (ObjectNode) read("schemas/examples/snapshot/trial-login.json");
	}

	static ObjectNode node(JsonNode document, int index) {
		return (ObjectNode) document.get("elements").get(index);
	}

	static JsonNode cases() throws IOException {
		return read("schemas/examples/snapshot/cases.json");
	}

	/** `base` with the case's RFC 6902 patch applied; add, remove and replace are all the cases use. */
	static JsonNode patched(JsonNode example) throws IOException {
		JsonNode document = trialLogin();
		for (JsonNode operation : example.get("patch")) {
			String op = operation.get("op").asString();
			String path = operation.get("path").asString();
			int slash = path.lastIndexOf('/');
			JsonNode parent = document.at(path.substring(0, slash));
			String key = path.substring(slash + 1).replace("~1", "/").replace("~0", "~");
			JsonNode value = operation.get("value");
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
				throw new IllegalArgumentException("no container at " + path + " in " + example.get("name"));
			}
		}
		return document;
	}

	static JsonNode read(String path) throws IOException {
		try (InputStream in = new ClassPathResource(path).getInputStream()) {
			return MAPPER.readTree(in);
		}
	}

}
