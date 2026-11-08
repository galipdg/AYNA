package com.ayna.server.tests;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import org.springframework.stereotype.Component;

import com.ayna.server.error.FieldError;
import com.ayna.server.schema.SchemaFile;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** The step schema (`schemas/step.schema.json`) and a validator for it. */
@Component
public class StepSchema {

	/** Step fields stored as JSON strings, since Neo4j properties cannot hold maps. */
	static final Set<String> JSON_FIELDS = Set.of("checkpoint", "row");

	private final SchemaFile file;

	public StepSchema(ObjectMapper mapper) {
		this.file = new SchemaFile(mapper, "schemas/step.schema.json");
	}

	/** The one document version this schema accepts (`version` is a `const`). */
	public String version() {
		return file.version();
	}

	/** A step's fields in the schema's order; responses list them in this order. */
	public List<String> stepFields() {
		List<String> fields = new ArrayList<>();
		file.node().path("$defs").path("step").path("properties").propertyNames().forEach(fields::add);
		return fields;
	}

	/** The `screen.element` pattern of a logical name (`$defs/logicalName`); repository objects use it too (#25). */
	public String logicalNamePattern() {
		return file.node().path("$defs").path("logicalName").path("pattern").asString();
	}

	/** One entry per violation, sorted by path; empty when the document is valid. */
	public List<FieldError> validate(JsonNode document) {
		return file.validate(document);
	}

	JsonNode schemaNode() {
		return file.node();
	}

}
