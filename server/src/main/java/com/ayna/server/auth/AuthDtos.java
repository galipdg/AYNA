package com.ayna.server.auth;

import java.time.Instant;

/** Request and response bodies of the login, account and API-token APIs. */
final class AuthDtos {

	private AuthDtos() {
	}

	record LoginRequest(String username, String password) {
	}

	/** `token` goes in `Authorization: Bearer` on every later request until `expiresAt`. */
	record LoginResponse(String token, Instant expiresAt, UserResponse user) {
	}

	record UserResponse(String id, String username, String role, Instant createdAt) {
	}

	record CreateUserRequest(String username, String password, String role) {
	}

	/** Either field may be left out; at least one must be given. */
	record UpdateUserRequest(String role, String password) {
	}

	record CreateTokenRequest(String name) {
	}

	record TokenResponse(String id, String name, Instant createdAt) {
	}

	/** The only time the secret is shown; the server keeps its hash. */
	record CreatedTokenResponse(String id, String name, Instant createdAt, String token) {
	}

}
