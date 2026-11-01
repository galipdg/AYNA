package com.ayna.server.apps;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionContext;
import org.springframework.stereotype.Service;

import com.ayna.server.apps.AppDtos.AppResponse;
import com.ayna.server.apps.AppDtos.VersionResponse;
import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.NotFoundException;

/**
 * Creates and lists applications and their versions. Duplicate names are checked in the
 * same write transaction as the create; there is no uniqueness constraint behind it, so
 * two concurrent creates of the same name can both succeed (see #128).
 */
@Service
public class AppService {

	private final Driver driver;

	public AppService(Driver driver) {
		this.driver = driver;
	}

	public AppResponse createApp(String name, String technology) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				if (exists(tx, "MATCH (a:Application {name: $name}) RETURN a LIMIT 1", Map.of("name", name))) {
					throw new ConflictException("Application already exists: " + name);
				}
				String id = UUID.randomUUID().toString();
				tx.run("CREATE (:Application {id: $id, name: $name, technology: $technology})",
						Map.of("id", id, "name", name, "technology", technology))
					.consume();
				return new AppResponse(id, name, technology);
			});
		}
	}

	public List<AppResponse> listApps() {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> tx.run("""
					MATCH (a:Application)
					RETURN a.id AS id, a.name AS name, a.technology AS technology
					ORDER BY a.name""")
				.list(r -> new AppResponse(r.get("id").asString(), r.get("name").asString(),
						r.get("technology").asString())));
		}
	}

	public VersionResponse createVersion(String appId, String version) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				requireApp(tx, appId);
				if (exists(tx, "MATCH (:Application {id: $appId})-[:HAS_VERSION]->(v:AppVersion {version: $version}) "
						+ "RETURN v LIMIT 1", Map.of("appId", appId, "version", version))) {
					throw new ConflictException("Version " + version + " already exists for application " + appId);
				}
				String id = UUID.randomUUID().toString();
				tx.run("""
						MATCH (a:Application {id: $appId})
						CREATE (a)-[:HAS_VERSION]->(:AppVersion {id: $id, version: $version})""",
						Map.of("appId", appId, "id", id, "version", version))
					.consume();
				return new VersionResponse(id, version);
			});
		}
	}

	/** Versions sorted by their version string (lexicographic, so "1.10" comes before "1.9"). */
	public List<VersionResponse> listVersions(String appId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				requireApp(tx, appId);
				return tx.run("""
						MATCH (:Application {id: $appId})-[:HAS_VERSION]->(v:AppVersion)
						RETURN v.id AS id, v.version AS version
						ORDER BY v.version""", Map.of("appId", appId))
					.list(r -> new VersionResponse(r.get("id").asString(), r.get("version").asString()));
			});
		}
	}

	private static void requireApp(TransactionContext tx, String appId) {
		if (!exists(tx, "MATCH (a:Application {id: $appId}) RETURN a LIMIT 1", Map.of("appId", appId))) {
			throw new NotFoundException("Application not found: " + appId);
		}
	}

	private static boolean exists(TransactionContext tx, String query, Map<String, Object> params) {
		return tx.run(query, params).hasNext();
	}

}
