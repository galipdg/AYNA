package com.ayna.server;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;

import org.neo4j.driver.exceptions.AuthenticationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationFailedEvent;
import org.springframework.context.ApplicationListener;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * When the server fails to start because Neo4j refused its password, logs one line that says so
 * and how to fix it (#208). The usual cause is a Neo4j volume created with an older `.env`: Neo4j
 * applies `NEO4J_AUTH` only when its volume is first created. Spring Boot still logs the original
 * exception with its stack trace right after this line.
 *
 * <p>
 * Registered in `META-INF/spring.factories`, not as a bean: a bean listener hears about a failed
 * start only if it was created before the bean that failed, and as a bean this one logged its line
 * twice (#208 task note).
 */
public class Neo4jAuthFailureHint implements ApplicationListener<ApplicationFailedEvent> {

	private static final Logger log = LoggerFactory.getLogger(Neo4jAuthFailureHint.class);

	@Override
	public void onApplicationEvent(ApplicationFailedEvent event) {
		if (!causedByAuthenticationFailure(event.getException())) {
			return;
		}
		ConfigurableApplicationContext context = event.getApplicationContext();
		String uri = "bolt://localhost:7687";
		String username = "neo4j";
		if (context != null) {
			uri = context.getEnvironment().getProperty("spring.neo4j.uri", uri);
			username = context.getEnvironment().getProperty("spring.neo4j.authentication.username", username);
		}
		log.error("Neo4j at {} refused the password for user '{}'. Neo4j keeps the password its volume was "
				+ "created with: if the volume predates your .env, run `docker compose down -v` (this deletes "
				+ "all graph data) or set NEO4J_PASSWORD back to the old password.", uri, username);
	}

	static boolean causedByAuthenticationFailure(Throwable failure) {
		Set<Throwable> seen = Collections.newSetFromMap(new IdentityHashMap<>());
		for (Throwable t = failure; t != null && seen.add(t); t = t.getCause()) {
			if (t instanceof AuthenticationException) {
				return true;
			}
		}
		return false;
	}

}
