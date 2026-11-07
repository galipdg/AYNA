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
			"TestCase", "Step", "Run", "StepResult", "HealingProposal", "Rule", "User", "AuthToken");

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
				Map.of("label", "Run", "property", "startedAt"), Map.of("label", "TestCase", "property", "name"));
	}

	@Test
	void migrationsAreRecorded() {
		List<Record> applied = driver.executableQuery("""
				MATCH (m:__Neo4jMigration) WHERE m.version <> 'BASELINE'
				RETURN m.version AS version, m.description AS description ORDER BY version""").execute().records();

		assertThat(applied).extracting(r -> r.get("version").asString() + " " + r.get("description").asString())
			.containsExactly("0001 graph schema v0", "0002 tests and objects belong to an application",
					"0003 accounts and tokens", "0005 one window per snapshot");
	}

	@Test
	void usernamesTokenHashesAndSnapshotIdsAreUnique() {
		List<String> constraints = driver.executableQuery("""
				SHOW CONSTRAINTS YIELD type, labelsOrTypes, properties
				WHERE type = 'UNIQUENESS' AND properties <> ['id'] AND NOT labelsOrTypes[0] STARTS WITH '__'
				RETURN labelsOrTypes[0] + '.' + properties[0] AS key""")
			.execute()
			.records()
			.stream()
			.map(r -> r.get("key").asString())
			.toList();

		assertThat(constraints).containsExactlyInAnyOrder("User.username", "AuthToken.tokenHash", "Window.snapshotId");
	}

}
