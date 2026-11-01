package com.ayna.server.tests;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;

import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

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
 * The step schema (`schemas/step.schema.json`, copied onto the classpath by the build) and a
 * validator for it. Remote fetching is off: the 2020-12 meta-schema ships inside the library,
 * and the server must not reach outside the closed network (NFR-29).
 */
@Component
public class StepSchema {

	/** Step fields stored as JSON strings, since Neo4j properties cannot hold maps. */
	static final Set<String> JSON_FIELDS = Set.of("checkpoint", "row");

	private final JsonNode schemaNode;

	private final Schema schema;

	public StepSchema(ObjectMapper mapper) {
		try (InputStream in = new ClassPathResource("schemas/step.schema.json").getInputStream()) {
			this.schemaNode = mapper.readTree(in);
		}
		catch (IOException ex) {
			throw new UncheckedIOException("cannot read the step schema", ex);
		}
		SchemaRegistryConfig config = SchemaRegistryConfig.builder()
			.pathType(PathType.JSON_PATH)
			.locale(Locale.ENGLISH)
			.build();
		SchemaRegistry registry = SchemaRegistry.withDefaultDialect(SpecificationVersion.DRAFT_2020_12,
				builder -> builder.schemaRegistryConfig(config).schemaLoader(loader -> loader.fetchRemoteResources(false)));
		this.schema = registry.getSchema(schemaNode);
	}

	/** The one document version this schema accepts (`version` is a `const`). */
	public String version() {
		return schemaNode.path("properties").path("version").path("const").asString();
	}

	/** A step's fields in the schema's order; responses list them in this order. */
	public List<String> stepFields() {
		List<String> fields = new ArrayList<>();
		schemaNode.path("$defs").path("step").path("properties").propertyNames().forEach(fields::add);
		return fields;
	}

	/** One entry per violation, sorted by path; empty when the document is valid. */
	public List<FieldError> validate(JsonNode document) {
		return schema.validate(document)
			.stream()
			.map(StepSchema::fieldError)
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

	JsonNode schemaNode() {
		return schemaNode;
	}

}
