package com.ayna.server.runs;

import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import com.ayna.server.auth.AccountService;
import com.ayna.server.runs.RunDtos.Events;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Live run status on `/ws/runs` (FR-20, NFR-06, ADR runs-api-and-live-updates). A client
 * subscribes to the tests it has open and gets their run events. Nothing is replayed: after
 * `subscribed`, and after a reconnect, the client reads the running run over REST and merges
 * by `stepIndex`. The security chain has already checked the upgrade request's Bearer token;
 * subscriptions live in memory, which is enough for one central server.
 */
@Component
class RunEvents extends TextWebSocketHandler {

	static final String PATH = "/ws/runs";

	private static final Logger log = LoggerFactory.getLogger(RunEvents.class);

	private static final int SEND_TIME_LIMIT_MS = 5_000;

	private static final int BUFFER_SIZE_LIMIT = 512 * 1024;

	/** Open connections by session id, wrapped so several request threads can send to one. */
	private final Map<String, WebSocketSession> connections = new ConcurrentHashMap<>();

	/** Session ids by test. */
	private final Map<String, Set<String>> subscribers = new ConcurrentHashMap<>();

	private final AccountService accounts;

	private final ObjectMapper mapper;

	RunEvents(AccountService accounts, ObjectMapper mapper) {
		this.accounts = accounts;
		this.mapper = mapper;
	}

	/** Sends the event to the test's subscribers. A client that cannot take it never fails the REST call. */
	void publish(String testId, Object event) {
		Set<String> ids = subscribers.get(testId);
		if (ids == null) {
			return;
		}
		TextMessage message = new TextMessage(mapper.writeValueAsString(event));
		ids.forEach(id -> send(connections.get(id), message));
	}

	/**
	 * Closes connections whose token has expired or was revoked (NFR-32). A failed check leaves
	 * them open: a database that is briefly away must not drop every watching client.
	 */
	@Scheduled(fixedDelay = 60, timeUnit = TimeUnit.SECONDS)
	void closeExpiredConnections() {
		connections.values().forEach(session -> {
			try {
				String header = session.getHandshakeHeaders().getFirst(HttpHeaders.AUTHORIZATION);
				if (accounts.authenticateHeader(header).isEmpty()) {
					close(session, CloseStatus.POLICY_VIOLATION.withReason("The session has ended"));
				}
			}
			catch (RuntimeException ex) {
				log.warn("Could not re-check the token of connection {}: {}", session.getId(), ex.getMessage());
			}
		});
	}

	@Override
	public void afterConnectionEstablished(WebSocketSession session) {
		connections.put(session.getId(),
				new ConcurrentWebSocketSessionDecorator(session, SEND_TIME_LIMIT_MS, BUFFER_SIZE_LIMIT));
	}

	@Override
	public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
		connections.remove(session.getId());
		subscribers.keySet().forEach(testId -> unsubscribe(testId, session.getId()));
	}

	@Override
	protected void handleTextMessage(WebSocketSession session, TextMessage text) {
		WebSocketSession connection = connections.get(session.getId());
		JsonNode message;
		try {
			message = mapper.readTree(text.getPayload());
		}
		catch (JacksonException ex) {
			sendError(connection, "The message is not JSON");
			return;
		}
		String type = message.path("type").asString("");
		String testId = message.path("testId").asString("");
		if (testId.isBlank()) {
			sendError(connection, "The message has no testId");
		}
		else if (type.equals("subscribe")) {
			subscribers.compute(testId, (key, ids) -> {
				Set<String> set = ids != null ? ids : ConcurrentHashMap.newKeySet();
				set.add(session.getId());
				return set;
			});
			send(connection, json(new Events.Subscribed(Events.SUBSCRIBED, testId)));
		}
		else if (type.equals("unsubscribe")) {
			unsubscribe(testId, session.getId());
		}
		else {
			sendError(connection, "Unknown message type: " + type);
		}
	}

	private void unsubscribe(String testId, String sessionId) {
		subscribers.computeIfPresent(testId, (key, ids) -> {
			ids.remove(sessionId);
			return ids.isEmpty() ? null : ids;
		});
	}

	private void sendError(WebSocketSession connection, String detail) {
		send(connection, json(new Events.Error(Events.ERROR, detail)));
	}

	private TextMessage json(Object event) {
		return new TextMessage(mapper.writeValueAsString(event));
	}

	/** A client too slow for the limits is dropped; it reconnects and catches up over REST. */
	private void send(WebSocketSession connection, TextMessage message) {
		if (connection == null) {
			return;
		}
		try {
			connection.sendMessage(message);
		}
		catch (IOException | RuntimeException ex) {
			log.info("Dropping connection {}: {}", connection.getId(), ex.getMessage());
			close(connection, CloseStatus.SESSION_NOT_RELIABLE);
		}
	}

	private void close(WebSocketSession connection, CloseStatus status) {
		try {
			connection.close(status);
		}
		catch (IOException | RuntimeException ex) {
			log.debug("Closing connection {} failed: {}", connection.getId(), ex.getMessage());
		}
	}

}
