package com.ayna.server.auth;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Session;
import org.neo4j.driver.TransactionContext;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.ayna.server.auth.AuthDtos.CreatedTokenResponse;
import com.ayna.server.auth.AuthDtos.LoginResponse;
import com.ayna.server.auth.AuthDtos.TokenResponse;
import com.ayna.server.auth.AuthDtos.UserResponse;
import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.NotFoundException;
import com.ayna.server.error.ApiExceptions.UnauthorizedException;

/**
 * Accounts, login sessions and API tokens (#60, ADR accounts-and-tokens). A removed account
 * keeps its node (`removedAt`), so user ids stored on old edits still resolve; it loses its
 * tokens and cannot log in. There is always at least one active admin.
 */
@Service
public class AccountService {

	static final Set<String> ROLES = Set.of(AynaPrincipal.ADMIN, AynaPrincipal.TESTER);

	static final Pattern USERNAME = Pattern.compile("[a-z0-9._-]{1,64}");

	static final int MIN_PASSWORD_LENGTH = 8;

	/** BCrypt reads at most 72 bytes; Spring refuses longer input instead of truncating it. */
	static final int MAX_PASSWORD_BYTES = 72;

	private static final String LOGIN_FAILED = "Wrong user name or password";

	private final Driver driver;

	private final PasswordEncoder encoder;

	private final Duration sessionTtl;

	/** Compared against when the user does not exist, so both failures take as long. */
	private final String dummyHash;

	public AccountService(Driver driver, PasswordEncoder encoder,
			@Value("${ayna.auth.session-ttl:12h}") Duration sessionTtl) {
		this.driver = driver;
		this.encoder = encoder;
		this.sessionTtl = sessionTtl;
		this.dummyHash = encoder.encode("not-a-password-" + UUID.randomUUID());
	}

	/** The account behind a Bearer token, if the token exists, has not expired and its account is active. */
	public Optional<AynaPrincipal> authenticate(String secret) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> tx.run("""
					MATCH (u:User)-[:HAS_TOKEN]->(t:AuthToken {tokenHash: $hash})
					WHERE u.removedAt IS NULL AND (t.expiresAt IS NULL OR t.expiresAt > datetime())
					RETURN u.id AS id, u.username AS username, u.role AS role""",
					Map.of("hash", Tokens.hash(secret)))
				.list(r -> new AynaPrincipal(r.get("id").asString(), r.get("username").asString(),
						r.get("role").asString()))
				.stream()
				.findFirst());
		}
	}

	/** A new session token; the same 401 for an unknown user and a wrong password. */
	public LoginResponse login(String username, String password) {
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				var found = tx.run("""
						MATCH (u:User {username: $username}) WHERE u.removedAt IS NULL
						RETURN u.passwordHash AS hash, u""", Map.of("username", normalise(username))).list();
				String hash = found.isEmpty() ? dummyHash : found.get(0).get("hash").asString();
				boolean matches = !tooLong(password) && encoder.matches(password, hash);
				if (found.isEmpty() || !matches) {
					throw new UnauthorizedException(LOGIN_FAILED);
				}
				UserResponse user = user(found.get(0));
				tx.run("""
						MATCH (:User {id: $id})-[:HAS_TOKEN]->(t:AuthToken {kind: 'session'})
						WHERE t.expiresAt <= datetime()
						DETACH DELETE t""", Map.of("id", user.id())).consume();
				String secret = Tokens.newSecret();
				Instant expiresAt = Instant.now().plus(sessionTtl);
				tx.run("""
						MATCH (u:User {id: $userId})
						CREATE (u)-[:HAS_TOKEN]->(:AuthToken {id: $id, kind: 'session', tokenHash: $hash,
						  createdAt: datetime(), expiresAt: $expiresAt})""",
						Map.of("userId", user.id(), "id", UUID.randomUUID().toString(), "hash", Tokens.hash(secret),
								"expiresAt", OffsetDateTime.ofInstant(expiresAt, ZoneOffset.UTC)))
					.consume();
				return new LoginResponse(secret, expiresAt, user);
			});
		}
	}

	/** Ends the session of `secret`; an API token is not ended this way. */
	public void logout(String secret) {
		try (Session session = driver.session()) {
			session.executeWriteWithoutResult(tx -> tx
				.run("MATCH (t:AuthToken {tokenHash: $hash, kind: 'session'}) DETACH DELETE t",
						Map.of("hash", Tokens.hash(secret)))
				.consume());
		}
	}

	public UserResponse getUser(String userId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> user(requireUser(tx, userId)));
		}
	}

	/** Active accounts, sorted by user name. */
	public List<UserResponse> listUsers() {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> tx
				.run("MATCH (u:User) WHERE u.removedAt IS NULL RETURN u ORDER BY u.username")
				.list(AccountService::user));
		}
	}

	public UserResponse createUser(String username, String password, String role) {
		String name = validUsername(username);
		String hash = encoder.encode(validPassword(password));
		String validRole = validRole(role);
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> create(tx, name, hash, validRole));
		}
	}

	/**
	 * Changes the role, the password or both. A new password ends the account's sessions, not
	 * its API tokens. The last active admin cannot be demoted.
	 */
	public UserResponse updateUser(String userId, String role, String password) {
		if (role == null && password == null) {
			throw new InvalidRequestException("$", "Give 'role', 'password' or both");
		}
		String validRole = role == null ? null : validRole(role);
		String hash = password == null ? null : encoder.encode(validPassword(password));
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				requireUser(tx, userId);
				if (AynaPrincipal.TESTER.equals(validRole)) {
					requireAnotherAdmin(tx, userId, "The last admin cannot become a tester");
				}
				Map<String, Object> params = new HashMap<>();
				params.put("id", userId);
				params.put("role", validRole);
				params.put("hash", hash);
				tx.run("""
						MATCH (u:User {id: $id})
						SET u.role = coalesce($role, u.role), u.passwordHash = coalesce($hash, u.passwordHash)""",
						params).consume();
				if (hash != null) {
					tx.run("MATCH (:User {id: $id})-[:HAS_TOKEN]->(t:AuthToken {kind: 'session'}) DETACH DELETE t",
							Map.of("id", userId)).consume();
				}
				return user(requireUser(tx, userId));
			});
		}
	}

	/** Removes the account: it keeps its node and name but loses every token. */
	public void removeUser(String userId) {
		try (Session session = driver.session()) {
			session.executeWriteWithoutResult(tx -> {
				requireUser(tx, userId);
				requireAnotherAdmin(tx, userId, "The last admin cannot be removed");
				tx.run("""
						MATCH (u:User {id: $id})
						OPTIONAL MATCH (u)-[:HAS_TOKEN]->(t:AuthToken)
						DETACH DELETE t
						WITH DISTINCT u
						SET u.removedAt = datetime()""", Map.of("id", userId)).consume();
			});
		}
	}

	/** A CI API token for the account; the secret is returned once. */
	public CreatedTokenResponse createApiToken(String userId, String name) {
		if (name == null || name.isBlank()) {
			throw new InvalidRequestException("$.name", "'name' must not be blank");
		}
		String secret = Tokens.newSecret();
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				requireUser(tx, userId);
				Record r = tx.run("""
						MATCH (u:User {id: $userId})
						CREATE (u)-[:HAS_TOKEN]->(t:AuthToken {id: $id, kind: 'api', name: $name, tokenHash: $hash,
						  createdAt: datetime()})
						RETURN t""", Map.of("userId", userId, "id", UUID.randomUUID().toString(), "name", name.strip(),
						"hash", Tokens.hash(secret)))
					.single();
				TokenResponse token = token(r);
				return new CreatedTokenResponse(token.id(), token.name(), token.createdAt(), secret);
			});
		}
	}

	/** The account's API tokens, oldest first; sessions are not listed. */
	public List<TokenResponse> listApiTokens(String userId) {
		try (Session session = driver.session()) {
			return session.executeRead(tx -> {
				requireUser(tx, userId);
				return tx.run("""
						MATCH (:User {id: $id})-[:HAS_TOKEN]->(t:AuthToken {kind: 'api'})
						RETURN t ORDER BY t.createdAt""", Map.of("id", userId))
					.list(AccountService::token);
			});
		}
	}

	public void revokeApiToken(String tokenId) {
		try (Session session = driver.session()) {
			session.executeWriteWithoutResult(tx -> {
				var deleted = tx.run("""
						MATCH (t:AuthToken {id: $id, kind: 'api'})
						DETACH DELETE t
						RETURN count(*) AS n""", Map.of("id", tokenId)).single().get("n").asInt();
				if (deleted == 0) {
					throw new NotFoundException("API token not found: " + tokenId);
				}
			});
		}
	}

	/** Creates the first admin unless an active admin exists; returns whether it did. */
	boolean createFirstAdmin(String username, String password) {
		String name = validUsername(username);
		String hash = encoder.encode(validPassword(password));
		try (Session session = driver.session()) {
			return session.executeWrite(tx -> {
				if (activeAdmins(tx) > 0) {
					return false;
				}
				if (tx.run("MATCH (u:User {username: $name}) RETURN u", Map.of("name", name)).hasNext()) {
					throw new IllegalStateException("AYNA_ADMIN_USERNAME '" + name
							+ "' belongs to an account that is not an active admin; choose another name");
				}
				create(tx, name, hash, AynaPrincipal.ADMIN);
				return true;
			});
		}
	}

	private static UserResponse create(TransactionContext tx, String name, String hash, String role) {
		if (tx.run("MATCH (u:User {username: $name}) RETURN u", Map.of("name", name)).hasNext()) {
			throw new ConflictException("User name already taken: " + name);
		}
		return user(tx.run("""
				CREATE (u:User {id: $id, username: $name, passwordHash: $hash, role: $role, createdAt: datetime()})
				RETURN u""", Map.of("id", UUID.randomUUID().toString(), "name", name, "hash", hash, "role", role))
			.single());
	}

	private static Record requireUser(TransactionContext tx, String userId) {
		var found = tx.run("MATCH (u:User {id: $id}) WHERE u.removedAt IS NULL RETURN u", Map.of("id", userId)).list();
		if (found.isEmpty()) {
			throw new NotFoundException("User not found: " + userId);
		}
		return found.get(0);
	}

	private static void requireAnotherAdmin(TransactionContext tx, String userId, String message) {
		boolean isAdmin = tx.run("MATCH (u:User {id: $id, role: 'admin'}) RETURN u", Map.of("id", userId)).hasNext();
		if (isAdmin && activeAdmins(tx) <= 1) {
			throw new ConflictException(message);
		}
	}

	private static int activeAdmins(TransactionContext tx) {
		return tx.run("MATCH (u:User {role: 'admin'}) WHERE u.removedAt IS NULL RETURN count(u) AS n")
			.single()
			.get("n")
			.asInt();
	}

	private static UserResponse user(Record r) {
		var u = r.get("u");
		return new UserResponse(u.get("id").asString(), u.get("username").asString(), u.get("role").asString(),
				u.get("createdAt").asZonedDateTime().toInstant());
	}

	private static TokenResponse token(Record r) {
		var t = r.get("t");
		return new TokenResponse(t.get("id").asString(), t.get("name").asString(),
				t.get("createdAt").asZonedDateTime().toInstant());
	}

	private static String normalise(String username) {
		return username == null ? "" : username.strip().toLowerCase(Locale.ROOT);
	}

	private static String validUsername(String username) {
		String name = normalise(username);
		if (!USERNAME.matcher(name).matches()) {
			throw new InvalidRequestException("$.username",
					"'username' must be 1 to 64 characters: letters a-z, digits, '.', '_' or '-'");
		}
		return name;
	}

	private static String validPassword(String password) {
		if (password == null || password.length() < MIN_PASSWORD_LENGTH) {
			throw new InvalidRequestException("$.password",
					"'password' must be at least " + MIN_PASSWORD_LENGTH + " characters");
		}
		if (tooLong(password)) {
			throw new InvalidRequestException("$.password",
					"'password' must be at most " + MAX_PASSWORD_BYTES + " bytes in UTF-8");
		}
		return password;
	}

	private static boolean tooLong(String password) {
		return password == null || password.getBytes(StandardCharsets.UTF_8).length > MAX_PASSWORD_BYTES;
	}

	private static String validRole(String role) {
		if (role == null || !ROLES.contains(role)) {
			throw new InvalidRequestException("$.role", "'role' must be 'admin' or 'tester'");
		}
		return role;
	}

}
