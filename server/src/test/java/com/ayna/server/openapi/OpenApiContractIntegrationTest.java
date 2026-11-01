package com.ayna.server.openapi;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import com.ayna.server.TestcontainersConfiguration;

/**
 * Generates `docs/api/openapi.yaml` from the running application (#31). The test rewrites the
 * file whenever the contract changes; CI then fails if the committed file differs, so commit
 * the regenerated file together with the REST change.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class OpenApiContractIntegrationTest {

	/** Surefire runs with `server/` as the working directory. */
	static final Path CONTRACT = Path.of("..", "docs", "api", "openapi.yaml");

	@Autowired
	MockMvc mvc;

	@Test
	void writesContractFile() throws Exception {
		String yaml = mvc.perform(get("/v3/api-docs.yaml"))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString(StandardCharsets.UTF_8);

		assertThat(yaml).contains("/api/health", "/api/apps", "/api/tests/{testId}/steps")
			.doesNotContain("localhost");

		if (!Files.exists(CONTRACT) || !Files.readString(CONTRACT).equals(yaml)) {
			Files.createDirectories(CONTRACT.getParent());
			Files.writeString(CONTRACT, yaml);
		}
	}

	/** Closed network: Swagger UI must not reach petstore.swagger.io or the online validator. */
	@Test
	void servesSwaggerUiWithoutExternalUrls() throws Exception {
		mvc.perform(get("/swagger-ui/index.html"))
			.andExpect(status().isOk())
			.andExpect(content().string(Matchers.containsString("Swagger UI")));
		mvc.perform(get("/swagger-ui/swagger-initializer.js"))
			.andExpect(status().isOk())
			.andExpect(content().string(Matchers.not(Matchers.containsString("petstore"))));
		mvc.perform(get("/v3/api-docs/swagger-config"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.validatorUrl").value("none"));
	}

}
