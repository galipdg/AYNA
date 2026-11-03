package com.ayna.server.openapi;

import static org.springframework.http.MediaType.APPLICATION_PROBLEM_JSON_VALUE;

import java.util.List;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.ArraySchema;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.IntegerSchema;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.ObjectSchema;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.servers.Server;
import org.springdoc.core.customizers.OperationCustomizer;
import org.springdoc.core.utils.SpringDocUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import tools.jackson.databind.JsonNode;

import com.ayna.server.error.ErrorResponses;

/**
 * Header of the generated REST contract (#31). The server URL is fixed to the request's
 * origin, so `docs/api/openapi.yaml` does not depend on the host or port it was generated on.
 * Error responses (#158) are shared components; an endpoint lists the ones it can return with
 * {@link ErrorResponses}.
 */
@Configuration(proxyBeanMethods = false)
class OpenApiConfig {

	/**
	 * Step documents, test files and snapshots travel as `JsonNode`, so the contract shows a plain
	 * object instead of Jackson's getters; the schemas in `schemas/` stay the real contract.
	 */
	static {
		SpringDocUtils.getConfig()
			.replaceWithSchema(JsonNode.class, new ObjectSchema()
				.description("JSON document, validated against its schema in schemas/ (steps: step.schema.json, snapshots: snapshot.schema.json)"));
	}

	@Bean
	OpenAPI aynaOpenApi() {
		return new OpenAPI()
			.info(new Info().title("AYNA server API")
				.version("v0")
				.description("REST API between the AYNA client and server. Generated from the code; do not edit by hand."))
			.servers(List.of(new Server().url("/")))
			.components(new Components().addSchemas("FieldError", fieldErrorSchema())
				.addSchemas("Problem", problemSchema())
				.addResponses(responseName(HttpStatus.BAD_REQUEST), problem("The request body or a field in it is invalid"))
				.addResponses(responseName(HttpStatus.NOT_FOUND), problem("An id in the path names nothing"))
				.addResponses(responseName(HttpStatus.CONFLICT), problem("A name is already taken")));
	}

	/** Adds the responses of {@link ErrorResponses} next to the generated success response. */
	@Bean
	OperationCustomizer errorResponses() {
		return (operation, handlerMethod) -> {
			ErrorResponses errors = handlerMethod.getMethodAnnotation(ErrorResponses.class);
			if (errors != null) {
				for (HttpStatus status : errors.value()) {
					operation.getResponses()
						.addApiResponse(String.valueOf(status.value()), new ApiResponse().$ref(responseName(status)));
				}
			}
			return operation;
		};
	}

	/** `NOT_FOUND` → `NotFound`, the component name of the status's response. */
	private static String responseName(HttpStatus status) {
		return status.getReasonPhrase().replace(" ", "");
	}

	/** RFC 9457 problem details, as `ApiErrorHandler` writes them. */
	private static Schema<?> problemSchema() {
		return new ObjectSchema().description("RFC 9457 problem details; the body of every 4xx response")
			.addProperty("type", new StringSchema().format("uri")
				.description("Problem kind, urn:ayna:error:<kind>; absent means about:blank. Treat an unknown type like about:blank"))
			.addProperty("title", new StringSchema().description("Short summary of the HTTP status"))
			.addProperty("status", new IntegerSchema())
			.addProperty("detail", new StringSchema()
				.description("Message for the user; names the field, object or id it concerns (NFR-15)"))
			.addProperty("instance", new StringSchema().format("uri"))
			.addProperty("errors", new ArraySchema().items(new Schema<>().$ref("FieldError"))
				.description("Failing fields, at most the first 50; only on a 400 caused by validation"))
			.addProperty("errorCount", new IntegerSchema().description("Number of failing fields, also those not listed in errors"))
			.required(List.of("title", "status"));
	}

	private static Schema<?> fieldErrorSchema() {
		return new ObjectSchema()
			.addProperty("path", new StringSchema().description("JSONPath (RFC 9535) into the request body, member names and array indices only, e.g. $.steps[2].value"))
			.addProperty("message", new StringSchema())
			.required(List.of("path", "message"));
	}

	private static ApiResponse problem(String description) {
		return new ApiResponse().description(description)
			.content(new Content().addMediaType(APPLICATION_PROBLEM_JSON_VALUE,
					new MediaType().schema(new Schema<>().$ref("Problem"))));
	}

}
