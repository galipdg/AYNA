package com.ayna.server.openapi;

import java.util.List;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.ObjectSchema;
import io.swagger.v3.oas.models.servers.Server;
import org.springdoc.core.utils.SpringDocUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.JsonNode;

/**
 * Header of the generated REST contract (#31). The server URL is fixed to the request's
 * origin, so `docs/api/openapi.yaml` does not depend on the host or port it was generated on.
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

	@Bean
	OpenAPI aynaOpenApi() {
		return new OpenAPI()
			.info(new Info().title("AYNA server API")
				.version("v0")
				.description("REST API between the AYNA client and server. Generated from the code; do not edit by hand."))
			.servers(List.of(new Server().url("/")));
	}

}
