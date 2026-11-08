package com.ayna.server;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.neo4j.driver.exceptions.AuthenticationException;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.neo4j.Neo4jContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * Starts the whole server against a Neo4j whose password is not the one the server has, as after a
 * `.env` change on an old volume (#208). Its own container: failed logins can lock the user out of
 * the shared one for the other tests.
 */
@Testcontainers
@ExtendWith(OutputCaptureExtension.class)
class Neo4jAuthFailureHintIntegrationTest {

	@Container
	static Neo4jContainer neo4j = new Neo4jContainer(DockerImageName.parse("neo4j:5.26-community"))
		.withAdminPassword("the-password-the-volume-has")
		.withNeo4jConfig("dbms.usage_report.enabled", "false");

	@Test
	void startFailsWithOneLineThatNamesTheFixAndKeepsTheOriginalException(CapturedOutput output) {
		var server = new SpringApplication(AynaServerApplication.class);

		assertThatThrownBy(() -> server.run("--spring.neo4j.uri=" + neo4j.getBoltUrl(),
				"--spring.neo4j.authentication.password=the-password-in-a-newer-env", "--server.port=0"))
			.hasRootCauseInstanceOf(AuthenticationException.class);

		assertThat(output.getOut().lines().filter(line -> line.contains("refused the password")))
			.singleElement()
			.asString()
			.contains("ERROR", "Neo4j at " + neo4j.getBoltUrl() + " refused the password for user 'neo4j'",
					"docker compose down -v");
		assertThat(output).contains("Caused by: org.neo4j.driver.exceptions.AuthenticationException");
	}

}
