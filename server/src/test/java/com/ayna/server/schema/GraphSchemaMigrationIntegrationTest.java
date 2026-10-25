package com.ayna.server.schema;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import com.ayna.server.TestcontainersConfiguration;

/** The server applies the graph schema migrations on start (needs Docker). */
@SpringBootTest
@Import(TestcontainersConfiguration.class)
class GraphSchemaMigrationIntegrationTest {

	static final List<String> LABELS = List.of("Application", "AppVersion", "Window", "Element", "RepoObject",
			"TestCase", "Step", "Run", "StepResult", "HealingProposal", "Rule");

	@Autowired
	Driver driver;

	/** neo4j-migrations adds its own `__Neo4jMigrationsLock` constraint; only domain labels count here. */
	@Test
	void everyLabelHasAUniqueIdConstraint() {
		List<Record> constraints = driver.executableQuery("""
				SHOW CONSTRAINTS YIELD type, entityType, labelsOrTypes, properties
				WHERE type = 'UNIQUENESS' AND entityType = 'NODE' AND properties = ['id']
				  AND NOT labelsOrTypes[0] STARTS WITH '__'
				RETURN labelsOrTypes[0] AS label""").execute().records();

		assertThat(constraints).map(r -> r.get("label").asString()).containsExactlyInAnyOrderElementsOf(LABELS);
	}

	@Test
	void lookupIndexesExist() {
		List<Map<String, Object>> indexes = driver.executableQuery("""
				SHOW INDEXES YIELD type, owningConstraint, labelsOrTypes, properties
				WHERE type = 'RANGE' AND owningConstraint IS NULL
				RETURN labelsOrTypes[0] AS label, properties[0] AS property""")
			.execute()
			.records()
			.stream()
			.map(Record::asMap)
			.toList();

		assertThat(indexes).contains(Map.of("label", "Application", "property", "name"),
				Map.of("label", "RepoObject", "property", "name"),
				Map.of("label", "Element", "property", "snapshotId"),
				Map.of("label", "Element", "property", "automationId"),
				Map.of("label", "Run", "property", "startedAt"));
	}

	@Test
	void migrationIsRecorded() {
		List<Record> applied = driver.executableQuery("""
				MATCH (m:__Neo4jMigration) WHERE m.version = '0001'
				RETURN m.description AS description""").execute().records();

		assertThat(applied).singleElement()
			.extracting(r -> r.get("description").asString())
			.isEqualTo("graph schema v0");
	}

}
