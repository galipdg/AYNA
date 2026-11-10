package com.ayna.server;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.neo4j.Neo4jContainer;
import org.testcontainers.utility.DockerImageName;

@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

	/** Same image and telemetry setting as docker-compose.yml. */
	@Bean
	@ServiceConnection
	Neo4jContainer neo4jContainer() {
		return new Neo4jContainer(DockerImageName.parse("neo4j:5.26-community"))
			.withNeo4jConfig("dbms.usage_report.enabled", "false");
	}

	/** Screenshots of a test context go to a fresh temporary folder, never to `data/screenshots` (#51). */
	@Bean
	DynamicPropertyRegistrar screenshotFolder() {
		try {
			String folder = Files.createTempDirectory("ayna-screenshots-").toString();
			return registry -> registry.add("ayna.screenshots.dir", () -> folder);
		}
		catch (IOException ex) {
			throw new UncheckedIOException(ex);
		}
	}

}
