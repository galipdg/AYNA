package com.ayna.server.openapi;

import static org.springframework.http.MediaType.APPLICATION_PROBLEM_JSON_VALUE;

import java.util.List;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.ArraySchema;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.IntegerSchema;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.ObjectSchema;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import org.springdoc.core.customizers.OperationCustomizer;
import org.springdoc.core.utils.SpringDocUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import tools.jackson.databind.JsonNode;

import com.ayna.server.auth.PublicEndpoint;
import com.ayna.server.error.ErrorResponses;

/**
 * Header of the generated REST contract (#31). The server URL is fixed to the request's
 * origin, so `docs/api/openapi.yaml` does not depend on the host or port it was generated on.
 * Error responses (#158) are shared components; an endpoint lists the ones it can return with
 * {@link ErrorResponses}. Every endpoint needs a Bearer token and can answer 401 unless it is
 * a {@link PublicEndpoint} (#60).
 */
@Configuration(proxyBeanMethods = false)
class OpenApiConfig {

	/**
	 * Step documents and test files travel as `JsonNode`, so the contract shows a plain object
	 * instead of Jackson's getters; the step schema in `schemas/` stays the real contract.
	 */
	static {
		SpringDocUtils.getConfig()
			.replaceWithSchema(JsonNode.class, new ObjectSchema()
				.description("JSON document; steps are validated against schemas/step.schema.json"));
	}

	static final String BEARER_AUTH = "bearerAuth";

	@Bean
	OpenAPI aynaOpenApi() {
		return new OpenAPI()
			.info(new Info().title("AYNA server API")
				.version("v0")
				.description("""
						REST API between the AYNA client and server. Generated from the code; do not edit by hand.

						**Live run status** is a WebSocket at `/ws/runs`, outside this document (ADR \
						runs-api-and-live-updates). The upgrade request carries the same Bearer token; without a valid \
						one it gets 401, and a token that expires or is revoked closes the connection with 1008 within \
						60 s. All messages are JSON objects.

						- Client to server: `{"type":"subscribe","testId":"…"}`, `{"type":"unsubscribe","testId":"…"}`
						- `subscribed`: `testId`
						- `run.started`: `testId`, `run`
						- `run.stepResult`: `testId`, `runId`, `stepIndex`, `stepId`, `status`, `duration`, `message`
						- `run.finished`: `testId`, `run`
						- `error`: `detail`

						`run` has the shape of `RunSummary`. Nothing is replayed: after `subscribed` and after a \
						reconnect, read `GET /api/tests/{testId}/runs?status=running` and `GET /api/runs/{runId}`, then \
						merge by `stepIndex`."""))
			.servers(List.of(new Server().url("/")))
			.addSecurityItem(new SecurityRequirement().addList(BEARER_AUTH))
			.components(new Components()
				.addSecuritySchemes(BEARER_AUTH, new SecurityScheme().type(SecurityScheme.Type.HTTP)
					.scheme("bearer")
					.description("Session token from POST /api/auth/login, or a CI API token (AYNA_SERVER_TOKEN)"))
				.addSchemas("FieldError", fieldErrorSchema())
				.addSchemas("Problem", problemSchema())
				.addResponses(responseName(HttpStatus.BAD_REQUEST), problem("The request body or a field in it is invalid"))
				.addResponses(responseName(HttpStatus.UNAUTHORIZED),
						problem("No valid session or API token; on login, a wrong user name or password"))
				.addResponses(responseName(HttpStatus.FORBIDDEN), problem("The account's role may not do this"))
				.addResponses(responseName(HttpStatus.NOT_FOUND), problem("An id in the path names nothing"))
				.addResponses(responseName(HttpStatus.CONFLICT),
						problem("The request conflicts with what is stored, such as a name already taken")));
	}

	/** Adds the responses of {@link ErrorResponses} next to the generated success response. */
	@Bean
	OperationCustomizer errorResponses() {
		return (operation, handlerMethod) -> {
			if (handlerMethod.hasMethodAnnotation(PublicEndpoint.class)) {
				operation.setSecurity(List.of());
			}
			else {
				addResponse(operation, HttpStatus.UNAUTHORIZED);
			}
			ErrorResponses errors = handlerMethod.getMethodAnnotation(ErrorResponses.class);
			if (errors != null) {
				for (HttpStatus status : errors.value()) {
					addResponse(operation, status);
				}
			}
			return operation;
		};
	}

	private static void addResponse(Operation operation, HttpStatus status) {
		operation.getResponses()
			.addApiResponse(String.valueOf(status.value()), new ApiResponse().$ref(responseName(status)));
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
