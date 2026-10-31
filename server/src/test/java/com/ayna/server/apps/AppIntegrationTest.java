package com.ayna.server.apps;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import com.ayna.server.TestcontainersConfiguration;

/** Applications and versions API against a real Neo4j started by Testcontainers (needs Docker). */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class AppIntegrationTest {

	static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

	@Autowired
	MockMvc mvc;

	@Autowired
	Driver driver;

	/** Domain nodes only: the migration tool's `__`-prefixed nodes must stay. */
	@BeforeEach
	void clearGraph() {
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
	}

	@Test
	void createsAnApplicationWithAUuid() throws Exception {
		createApp("Notepad", "win32").andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(matchesPattern(UUID_PATTERN)))
			.andExpect(jsonPath("$.name").value("Notepad"))
			.andExpect(jsonPath("$.technology").value("win32"))
			.andExpect(header().string("Location", matchesPattern("/api/apps/" + UUID_PATTERN)));
	}

	@Test
	void duplicateApplicationNameIsAConflict() throws Exception {
		createApp("Notepad", "win32").andExpect(status().isCreated());
		createApp("Notepad", "uia").andExpect(status().isConflict())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(409))
			.andExpect(jsonPath("$.title").value("Conflict"))
			.andExpect(jsonPath("$.detail").value("Application already exists: Notepad"));
	}

	@Test
	void blankApplicationFieldsAreRejected() throws Exception {
		createApp(" ", "win32").andExpect(status().isBadRequest())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(400))
			.andExpect(jsonPath("$.detail").value("'name' must not be blank"))
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.name")))
			.andExpect(jsonPath("$.errors[0].message").value("'name' must not be blank"));
		mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON).content("{\"name\": \"Notepad\"}"))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.technology")));
	}

	@Test
	void listsApplicationsSortedByName() throws Exception {
		createApp("Paint", "win32");
		createApp("Calculator", "uwp");
		createApp("Notepad", "win32");

		mvc.perform(get("/api/apps"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.length()").value(3))
			.andExpect(jsonPath("$[*].name").value(contains("Calculator", "Notepad", "Paint")));
	}

	@Test
	void createsAndListsVersionsOfAnApplication() throws Exception {
		String appId = appId(createApp("Notepad", "win32"));
		String otherId = appId(createApp("Paint", "win32"));

		createVersion(appId, "2.0").andExpect(status().isCreated())
			.andExpect(jsonPath("$.id").value(matchesPattern(UUID_PATTERN)))
			.andExpect(jsonPath("$.version").value("2.0"));
		createVersion(appId, "1.0").andExpect(status().isCreated());
		createVersion(otherId, "1.0").andExpect(status().isCreated());

		mvc.perform(get("/api/apps/{id}/versions", appId))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[*].version").value(contains("1.0", "2.0")));
	}

	@Test
	void duplicateVersionIsAConflict() throws Exception {
		String appId = appId(createApp("Notepad", "win32"));

		createVersion(appId, "1.0").andExpect(status().isCreated());
		createVersion(appId, "1.0").andExpect(status().isConflict())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.detail").value(containsString("Version 1.0 already exists")));
	}

	@Test
	void blankVersionIsRejected() throws Exception {
		String appId = appId(createApp("Notepad", "win32"));

		createVersion(appId, " ").andExpect(status().isBadRequest())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.errors[*].path").value(contains("$.version")));
	}

	@Test
	void versionsOfAnUnknownApplicationAreNotFound() throws Exception {
		String unknown = "00000000-0000-0000-0000-000000000000";

		createVersion(unknown, "1.0").andExpect(status().isNotFound())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(404))
			.andExpect(jsonPath("$.title").value("Not Found"))
			.andExpect(jsonPath("$.detail").value("Application not found: " + unknown));
		mvc.perform(get("/api/apps/{id}/versions", unknown)).andExpect(status().isNotFound())
			.andExpect(jsonPath("$.detail").value("Application not found: " + unknown));
	}

	private ResultActions createApp(String name, String technology) throws Exception {
		return mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON)
			.content("{\"name\": \"%s\", \"technology\": \"%s\"}".formatted(name, technology)));
	}

	private ResultActions createVersion(String appId, String version) throws Exception {
		return mvc.perform(post("/api/apps/{id}/versions", appId).contentType(MediaType.APPLICATION_JSON)
			.content("{\"version\": \"%s\"}".formatted(version)));
	}

	private static String appId(ResultActions result) throws Exception {
		return JsonPath.read(result.andReturn().getResponse().getContentAsString(), "$.id");
	}

}
