package com.ayna.server.health;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;

import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.neo4j.driver.exceptions.ServiceUnavailableException;
import org.springframework.http.HttpStatus;

class HealthControllerTest {

	@Test
	void reportsDbDownWhenNeo4jIsUnreachable() {
		Driver driver = mock(Driver.class);
		doThrow(new ServiceUnavailableException("no route")).when(driver).verifyConnectivity();

		var response = new HealthController(driver).health();

		assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
		assertThat(response.getBody()).containsEntry("db", "DOWN");
	}

}
