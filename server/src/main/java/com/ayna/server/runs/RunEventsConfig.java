package com.ayna.server.runs;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * Registers `/ws/runs`. The upgrade request is an ordinary GET, so `auth/SecurityConfig` asks
 * for a Bearer token as on every other path (NFR-32). Scheduling is for {@link RunEvents}'s
 * token re-check.
 */
@Configuration(proxyBeanMethods = false)
@EnableWebSocket
@EnableScheduling
class RunEventsConfig implements WebSocketConfigurer {

	private final RunEvents events;

	RunEventsConfig(RunEvents events) {
		this.events = events;
	}

	@Override
	public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
		registry.addHandler(events, RunEvents.PATH);
	}

}
