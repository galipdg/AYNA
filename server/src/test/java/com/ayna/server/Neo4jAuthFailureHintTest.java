package com.ayna.server;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.neo4j.driver.exceptions.AuthenticationException;
import org.neo4j.driver.exceptions.ServiceUnavailableException;
import org.springframework.beans.factory.BeanCreationException;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.event.ApplicationFailedEvent;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

@ExtendWith(OutputCaptureExtension.class)
class Neo4jAuthFailureHintTest {

	@Test
	void staysQuietForOtherStartupFailures(CapturedOutput output) {
		new Neo4jAuthFailureHint().onApplicationEvent(failed(new ServiceUnavailableException("no route")));

		assertThat(output).doesNotContain("refused the password");
	}

	@Test
	void findsTheRefusalBelowTheBeanFailureWithoutAContext(CapturedOutput output) {
		new Neo4jAuthFailureHint()
			.onApplicationEvent(failed(new AuthenticationException("Neo.ClientError.Security.Unauthorized", "no")));

		assertThat(output).contains("Neo4j at bolt://localhost:7687 refused the password for user 'neo4j'")
			.contains("docker compose down -v");
	}

	/** The shape seen at startup: the migrations bean fails, the driver's exception is its cause. */
	private static ApplicationFailedEvent failed(RuntimeException cause) {
		var failure = new BeanCreationException("neo4jMigrationsInitializer", cause.getMessage(), cause);
		return new ApplicationFailedEvent(new SpringApplication(), new String[0], null, failure);
	}

}
