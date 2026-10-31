package com.ayna.server.auth;

import java.net.URI;
import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AuthDtos.CreateTokenRequest;
import com.ayna.server.auth.AuthDtos.CreateUserRequest;
import com.ayna.server.auth.AuthDtos.CreatedTokenResponse;
import com.ayna.server.auth.AuthDtos.TokenResponse;
import com.ayna.server.auth.AuthDtos.UpdateUserRequest;
import com.ayna.server.auth.AuthDtos.UserResponse;
import com.ayna.server.error.ErrorResponses;

/** Accounts and their CI API tokens; admins only (FR-39, `SecurityConfig`). */
@RestController
@RequestMapping("/api")
public class UserController {

	private final AccountService accounts;

	public UserController(AccountService accounts) {
		this.accounts = accounts;
	}

	@ErrorResponses({ HttpStatus.FORBIDDEN })
	@GetMapping("/users")
	public List<UserResponse> listUsers() {
		return accounts.listUsers();
	}

	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.FORBIDDEN, HttpStatus.CONFLICT })
	@PostMapping("/users")
	@ResponseStatus(HttpStatus.CREATED)
	public ResponseEntity<UserResponse> createUser(@RequestBody CreateUserRequest request) {
		UserResponse user = accounts.createUser(request.username(), request.password(), request.role());
		return ResponseEntity.created(URI.create("/api/users/" + user.id())).body(user);
	}

	/** A new password ends the account's sessions; the last admin cannot become a tester (409). */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND,
			HttpStatus.CONFLICT })
	@PatchMapping("/users/{userId}")
	public UserResponse updateUser(@PathVariable String userId, @RequestBody UpdateUserRequest request) {
		return accounts.updateUser(userId, request.role(), request.password());
	}

	/** The account can no longer log in; its name stays on what it did. The last admin cannot go (409). */
	@ErrorResponses({ HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT })
	@DeleteMapping("/users/{userId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void removeUser(@PathVariable String userId) {
		accounts.removeUser(userId);
	}

	/** The `token` in the answer is shown only this once. */
	@ErrorResponses({ HttpStatus.BAD_REQUEST, HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND })
	@PostMapping("/users/{userId}/tokens")
	@ResponseStatus(HttpStatus.CREATED)
	public CreatedTokenResponse createToken(@PathVariable String userId, @RequestBody CreateTokenRequest request) {
		return accounts.createApiToken(userId, request.name());
	}

	@ErrorResponses({ HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND })
	@GetMapping("/users/{userId}/tokens")
	public List<TokenResponse> listTokens(@PathVariable String userId) {
		return accounts.listApiTokens(userId);
	}

	@ErrorResponses({ HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND })
	@DeleteMapping("/tokens/{tokenId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void revokeToken(@PathVariable String tokenId) {
		accounts.revokeApiToken(tokenId);
	}

}
