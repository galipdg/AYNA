package com.ayna.server.schema;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Locale;

import org.springframework.core.io.ClassPathResource;

import com.ayna.server.error.FieldError;
import com.networknt.schema.Error;
import com.networknt.schema.Schema;
import com.networknt.schema.SchemaRegistry;
import com.networknt.schema.SchemaRegistryConfig;
import com.networknt.schema.SpecificationVersion;
import com.networknt.schema.path.PathType;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * One shared contract from `schemas/` (copied onto the classpath by the build) and a validator
 * for it. Remote fetching is off: the 2020-12 meta-schema ships inside the library, and the
 * server must not reach outside the closed network (NFR-29).
 */
public final class SchemaFile {

	private final JsonNode node;

	private final Schema schema;

	/** `path` is the classpath location, e.g. `schemas/step.schema.json`. */
	public SchemaFile(ObjectMapper mapper, String path) {
		try (InputStream in = new ClassPathResource(path).getInputStream()) {
			this.node = mapper.readTree(in);
		}
		catch (IOException ex) {
			throw new UncheckedIOException("cannot read " + path, ex);
		}
		SchemaRegistryConfig config = SchemaRegistryConfig.builder()
			.pathType(PathType.JSON_PATH)
			.locale(Locale.ENGLISH)
			.build();
		SchemaRegistry registry = SchemaRegistry.withDefaultDialect(SpecificationVersion.DRAFT_2020_12,
				builder -> builder.schemaRegistryConfig(config).schemaLoader(loader -> loader.fetchRemoteResources(false)));
		this.schema = registry.getSchema(node);
	}

	/** The one document version this schema accepts (`version` is a `const`). */
	public String version() {
		return node.path("properties").path("version").path("const").asString();
	}

	public JsonNode node() {
		return node;
	}

	/** One entry per violation, sorted by path; empty when the document is valid. */
	public List<FieldError> validate(JsonNode document) {
		return schema.validate(document)
			.stream()
			.map(SchemaFile::fieldError)
			.distinct()
			.sorted((a, b) -> a.path().compareTo(b.path()))
			.toList();
	}

	/**
	 * Points the error at the field itself: the library reports a missing or extra property at
	 * its parent object, and a forbidden field (`false` subschema) as "schema for 'x' is false".
	 */
	private static FieldError fieldError(Error error) {
		String path = error.getInstanceLocation().toString();
		String keyword = error.getKeyword();
		if (("required".equals(keyword) || "additionalProperties".equals(keyword)) && error.getProperty() != null) {
			return new FieldError(path + "." + error.getProperty(), error.getMessage());
		}
		if ("false".equals(keyword)) {
			String field = path.substring(path.lastIndexOf('.') + 1);
			return new FieldError(path, "'" + field + "' is not allowed here");
		}
		return new FieldError(path, error.getMessage());
	}

}
