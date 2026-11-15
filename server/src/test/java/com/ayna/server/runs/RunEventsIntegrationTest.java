package com.ayna.server.runs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.WebSocket;
import java.net.http.WebSocketHandshakeException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.neo4j.driver.Driver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Import;

import com.ayna.server.TestcontainersConfiguration;
import com.ayna.server.auth.AccountService;
import com.ayna.server.auth.AynaPrincipal;
import com.ayna.server.schema.SchemaFile;
import com.ayna.server.tests.StepSchema;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * `/ws/runs` on a real port, with a real client that sends the Bearer header as the Electron
 * main process does, and real logins (needs Docker). Every message the server sends, and every
 * well-formed one the test sends, is checked against the frozen contract
 * `schemas/ws-runs.schema.json` (#52).
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfiguration.class)
class RunEventsIntegrationTest {

	static final String PASSWORD = "admin-password-1";

	/** NFR-06: a step's status reaches every client within 1 s. */
	static final Duration LIVE = Duration.ofSeconds(1);

	static final Duration QUIET = Duration.ofMillis(300);

	@LocalServerPort
	int port;

	@Autowired
	Driver driver;

	@Autowired
	AccountService accounts;

	@Autowired
	RunEvents events;

	@Autowired
	ObjectMapper mapper;

	@Autowired
	StepSchema stepSchema;

	SchemaFile contract;

	final HttpClient http = HttpClient.newHttpClient();

	String token;

	String testId;

	String versionId;

	Listener open;

	@BeforeEach
	void setUp() throws Exception {
		contract = new SchemaFile(mapper, "schemas/ws-runs.schema.json");
		driver.executableQuery("""
				MATCH (n) WHERE NOT any(l IN labels(n) WHERE l STARTS WITH '__')
				DETACH DELETE n""").execute();
		accounts.createUser("Admin", PASSWORD, AynaPrincipal.ADMIN);
		token = login();
		String appId = post("/api/apps", Map.of("name", "Müşteri Kayıt", "technology", "PySide6")).path("id").asString();
		versionId = post("/api/apps/" + appId + "/versions", Map.of("version", "1.0.0")).path("id").asString();
		driver.executableQuery("""
				MATCH (a:Application {id: $appId})
				CREATE (a)-[:HAS_OBJECT]->(:RepoObject {id: randomUUID(), name: 'login.loginButton'})""")
			.withParameters(Map.of("appId", appId))
			.execute();
		testId = newTest(appId, "Giriş");
	}

	@AfterEach
	void closeSocket() {
		if (open != null && open.socket != null) {
			open.socket.abort();
		}
	}

	@Test
	void theHandshakeNeedsAValidToken() {
		assertThat(handshakeStatus(null)).isEqualTo(401);
		assertThat(handshakeStatus("not-a-token")).isEqualTo(401);
	}

	@Test
	void aWatchingClientSeesARunLive() throws Exception {
		Listener watcher = connect(token);
		subscribe(watcher, testId);

		JsonNode run = post("/api/runs", Map.of("testId", testId, "appVersionId", versionId));
		String runId = run.path("id").asString();
		JsonNode started = watcher.next(LIVE);
		assertThat(started.path("type").asString()).isEqualTo("run.started");
		assertThat(started.path("testId").asString()).isEqualTo(testId);
		assertThat(started.path("run").path("id").asString()).isEqualTo(runId);
		assertThat(started.path("run").path("status").asString()).isEqualTo("running");
		assertThat(started.path("run").path("startedBy").path("username").asString()).isEqualTo("admin");
		assertThat(started.path("run").has("document")).isFalse();

		String stepId = run.path("document").path("steps").path(0).path("id").asString();
		put("/api/runs/" + runId + "/results/0", Map.of("runId", runId, "stepIndex", 0, "stepId", stepId, "status",
				"passed", "durationMs", 40, "message", "tamam"));
		JsonNode step = watcher.next(LIVE);
		assertThat(step.path("type").asString()).isEqualTo("run.stepResult");
		assertThat(step.path("testId").asString()).isEqualTo(testId);
		assertThat(step.path("runId").asString()).isEqualTo(runId);
		assertThat(step.path("stepIndex").asInt()).isZero();
		assertThat(step.path("stepId").asString()).isEqualTo(stepId);
		assertThat(step.path("status").asString()).isEqualTo("passed");
		assertThat(step.path("durationMs").asLong()).isEqualTo(40);
		assertThat(step.path("message").asString()).isEqualTo("tamam");
		assertThat(step.has("category")).isTrue();
		assertThat(step.path("category").isNull()).isTrue();

		post("/api/runs/" + runId + "/finish", Map.of("status", "passed"));
		JsonNode finished = watcher.next(LIVE);
		assertThat(finished.path("type").asString()).isEqualTo("run.finished");
		assertThat(finished.path("run").path("status").asString()).isEqualTo("passed");
		assertThat(finished.path("run").path("durationMs").isNumber()).isTrue();
	}

	@Test
	void repeatsAreNotSentAgain() throws Exception {
		Listener watcher = connect(token);
		subscribe(watcher, testId);
		JsonNode run = post("/api/runs", Map.of("testId", testId, "appVersionId", versionId));
		String runId = run.path("id").asString();
		watcher.next(LIVE);
		Map<String, Object> result = Map.of("runId", runId, "stepIndex", 0, "stepId",
				run.path("document").path("steps").path(0).path("id").asString(), "status", "passed");

		put("/api/runs/" + runId + "/results/0", result);
		watcher.next(LIVE);
		put("/api/runs/" + runId + "/results/0", result);
		assertThat(watcher.nothingFor(QUIET)).isTrue();

		post("/api/runs/" + runId + "/finish", Map.of("status", "passed"));
		watcher.next(LIVE);
		post("/api/runs/" + runId + "/finish", Map.of("status", "passed"));
		assertThat(watcher.nothingFor(QUIET)).isTrue();
	}

	@Test
	void onlySubscribersOfTheTestHearOfIt() throws Exception {
		Listener other = connect(token);
		subscribe(other, "some-other-test");

		post("/api/runs", Map.of("testId", testId, "appVersionId", versionId));

		assertThat(other.nothingFor(QUIET)).isTrue();
	}

	@Test
	void unsubscribingStopsTheEvents() throws Exception {
		Listener watcher = connect(token);
		subscribe(watcher, testId);
		watcher.sendValid(Map.of("type", "unsubscribe", "testId", testId));
		// A later subscribe answers on the same connection, so the unsubscribe has been handled.
		subscribe(watcher, "some-other-test");

		post("/api/runs", Map.of("testId", testId, "appVersionId", versionId));

		assertThat(watcher.nothingFor(QUIET)).isTrue();
	}

	@Test
	void aMessageTheServerCannotReadGetsAnErrorAndTheConnectionStays() throws Exception {
		Listener watcher = connect(token);

		watcher.socket.sendText("not json", true).get(5, TimeUnit.SECONDS);
		assertThat(watcher.next(LIVE).path("type").asString()).isEqualTo("error");
		watcher.send(Map.of("type", "subscribe"));
		assertThat(watcher.next(LIVE).path("detail").asString()).contains("testId");
		watcher.send(Map.of("type", "dance", "testId", testId));
		assertThat(watcher.next(LIVE).path("detail").asString()).contains("dance");
		watcher.send(Map.of("type", Map.of("a", 1), "testId", Map.of("b", 2)));
		assertThat(watcher.next(LIVE).path("type").asString()).isEqualTo("error");
		watcher.send(Map.of("type", "subscribe", "testId", List.of(1)));
		assertThat(watcher.next(LIVE).path("type").asString()).isEqualTo("error");
		watcher.socket.sendText("[1]", true).get(5, TimeUnit.SECONDS);
		assertThat(watcher.next(LIVE).path("type").asString()).isEqualTo("error");

		subscribe(watcher, testId);
	}

	@Test
	void aRevokedTokenClosesTheConnectionAndAValidOneStays() throws Exception {
		Listener keeps = connect(token);
		String second = login();
		Listener loses = connect(second);
		subscribe(keeps, testId);
		subscribe(loses, testId);

		logout(second);
		events.closeExpiredConnections();

		assertThat(loses.closedWith(LIVE)).isEqualTo(1008);
		post("/api/runs", Map.of("testId", testId, "appVersionId", versionId));
		assertThat(keeps.next(LIVE).path("type").asString()).isEqualTo("run.started");
		keeps.socket.abort();
	}

	private String newTest(String appId, String name) throws Exception {
		String id = post("/api/apps/" + appId + "/tests", Map.of("name", name)).path("id").asString();
		put("/api/tests/" + id + "/steps", Map.of("version", stepSchema.version(), "steps",
				List.of(Map.of("keyword", "Click", "target", "login.loginButton"))));
		return id;
	}

	private void subscribe(Listener listener, String test) throws Exception {
		listener.sendValid(Map.of("type", "subscribe", "testId", test));
		JsonNode reply = listener.next(LIVE);
		assertThat(reply.path("type").asString()).isEqualTo("subscribed");
		assertThat(reply.path("testId").asString()).isEqualTo(test);
	}

	private Listener connect(String bearer) throws Exception {
		Listener listener = new Listener();
		listener.socket = builder(bearer).buildAsync(socketUri(), listener).get(5, TimeUnit.SECONDS);
		open = listener;
		return listener;
	}

	private int handshakeStatus(String bearer) {
		var failure = new Object() {
			int status;
		};
		assertThatThrownBy(() -> builder(bearer).buildAsync(socketUri(), new Listener()).get(5, TimeUnit.SECONDS))
			.isInstanceOf(ExecutionException.class)
			.satisfies(ex -> failure.status = ((WebSocketHandshakeException) ex.getCause()).getResponse().statusCode());
		return failure.status;
	}

	private WebSocket.Builder builder(String bearer) {
		WebSocket.Builder builder = http.newWebSocketBuilder();
		return bearer == null ? builder : builder.header("Authorization", "Bearer " + bearer);
	}

	private URI socketUri() {
		return URI.create("ws://127.0.0.1:" + port + RunEvents.PATH);
	}

	private String login() throws Exception {
		HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/auth/login"))
			.header("Content-Type", "application/json")
			.POST(HttpRequest.BodyPublishers.ofString(
					mapper.writeValueAsString(Map.of("username", "admin", "password", PASSWORD))))
			.build();
		HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
		assertThat(response.statusCode()).isEqualTo(200);
		return mapper.readTree(response.body()).path("token").asString();
	}

	private void logout(String secret) throws Exception {
		HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/auth/logout"))
			.header("Authorization", "Bearer " + secret)
			.POST(HttpRequest.BodyPublishers.noBody())
			.build();
		assertThat(http.send(request, HttpResponse.BodyHandlers.discarding()).statusCode()).isLessThan(300);
	}

	private JsonNode post(String path, Object body) throws Exception {
		return send(path, "POST", body);
	}

	private JsonNode put(String path, Object body) throws Exception {
		return send(path, "PUT", body);
	}

	private JsonNode send(String path, String method, Object body) throws Exception {
		HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path))
			.header("Authorization", "Bearer " + token)
			.header("Content-Type", "application/json")
			.method(method, HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
			.build();
		HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
		assertThat(response.statusCode()).as(method + " " + path + ": " + response.body()).isLessThan(300);
		return mapper.readTree(response.body());
	}

	/** Collects what the server sends. */
	final class Listener implements WebSocket.Listener {

		final BlockingQueue<JsonNode> received = new LinkedBlockingQueue<>();

		final CompletableFuture<Integer> closed = new CompletableFuture<>();

		final StringBuilder partial = new StringBuilder();

		WebSocket socket;

		@Override
		public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
			partial.append(data);
			if (last) {
				received.add(mapper.readTree(partial.toString()));
				partial.setLength(0);
			}
			webSocket.request(1);
			return null;
		}

		@Override
		public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
			closed.complete(statusCode);
			return null;
		}

		void send(Map<String, Object> message) throws Exception {
			socket.sendText(mapper.writeValueAsString(message), true).get(5, TimeUnit.SECONDS);
		}

		/** Sends a message the contract allows, after checking that it does. */
		void sendValid(Map<String, Object> message) throws Exception {
			assertThat(contract.validate(mapper.valueToTree(message))).as("client message %s", message).isEmpty();
			send(message);
		}

		/** The next message from the server, which must match the contract. */
		JsonNode next(Duration within) throws InterruptedException {
			JsonNode message = received.poll(within.toMillis(), TimeUnit.MILLISECONDS);
			assertThat(message).as("a message within " + within).isNotNull();
			assertThat(contract.validate(message)).as("server message %s", message).isEmpty();
			return message;
		}

		boolean nothingFor(Duration quiet) throws InterruptedException {
			return received.poll(quiet.toMillis(), TimeUnit.MILLISECONDS) == null;
		}

		int closedWith(Duration within) throws Exception {
			return closed.get(within.toMillis(), TimeUnit.MILLISECONDS);
		}

	}

}
