package com.ayna.server.health;

import java.util.Map;

import org.neo4j.driver.Driver;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.PublicEndpoint;

/** Reports whether the server is up and can reach Neo4j. */
@RestController
public class HealthController {

	private final Driver driver;

	public HealthController(Driver driver) {
		this.driver = driver;
	}

	/** Public: the Compose healthcheck and the client's first-run check (SC-02) call it before any login. */
	@PublicEndpoint
	@GetMapping("/api/health")
	public ResponseEntity<Map<String, String>> health() {
		try {
			driver.verifyConnectivity();
			return ResponseEntity.ok(Map.of("status", "UP", "db", "UP"));
		}
		catch (RuntimeException ex) {
			return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(Map.of("status", "DOWN", "db", "DOWN"));
		}
	}

}
