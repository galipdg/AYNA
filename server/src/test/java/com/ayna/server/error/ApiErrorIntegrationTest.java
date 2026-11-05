package com.ayna.server.error;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.ayna.server.SignedIn;
import com.ayna.server.TestcontainersConfiguration;

/** Errors Spring raises before a controller runs get the same problem-details body (#158). */
@SpringBootTest
@AutoConfigureMockMvc
@Import({ TestcontainersConfiguration.class, SignedIn.class })
class ApiErrorIntegrationTest {

	@Autowired
	MockMvc mvc;

	@Test
	void unreadableJsonIsAProblem() throws Exception {
		mvc.perform(post("/api/apps").contentType(MediaType.APPLICATION_JSON).content("{\"name\": "))
			.andExpect(status().isBadRequest())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(400))
			.andExpect(jsonPath("$.title").value("Bad Request"));
	}

	@Test
	void unknownPathIsAProblem() throws Exception {
		mvc.perform(get("/api/no-such-thing"))
			.andExpect(status().isNotFound())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(404));
	}

	@Test
	void wrongMethodIsAProblem() throws Exception {
		mvc.perform(delete("/api/apps"))
			.andExpect(status().isMethodNotAllowed())
			.andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
			.andExpect(jsonPath("$.status").value(405));
	}

}
