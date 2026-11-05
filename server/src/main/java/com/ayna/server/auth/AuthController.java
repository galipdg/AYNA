package com.ayna.server.auth;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.ayna.server.auth.AuthDtos.LoginRequest;
import com.ayna.server.auth.AuthDtos.LoginResponse;
import com.ayna.server.auth.AuthDtos.UserResponse;
import com.ayna.server.error.ErrorResponses;

/** Login, logout and the current account (#60). */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

	private final AccountService accounts;

	public AuthController(AccountService accounts) {
		this.accounts = accounts;
	}

	@PublicEndpoint
	@ErrorResponses({ HttpStatus.UNAUTHORIZED })
	@PostMapping("/login")
	public LoginResponse login(@RequestBody LoginRequest request) {
		return accounts.login(request.username(), request.password());
	}

	/** Ends the session the request was sent with. */
	@PostMapping("/logout")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void logout(HttpServletRequest request) {
		BearerTokenFilter.bearerToken(request).ifPresent(accounts::logout);
	}

	@GetMapping("/me")
	public UserResponse me(@AuthenticationPrincipal AynaPrincipal me) {
		return accounts.getUser(me.userId());
	}

}
