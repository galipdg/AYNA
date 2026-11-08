package com.ayna.server.auth;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Turns `Authorization: Bearer <token>` into the request's {@link AynaPrincipal}. A missing,
 * unknown or expired token leaves the request anonymous; the security chain then answers 401
 * wherever an account is required.
 */
class BearerTokenFilter extends OncePerRequestFilter {

	private static final String PREFIX = "Bearer ";

	private final AccountService accounts;

	BearerTokenFilter(AccountService accounts) {
		this.accounts = accounts;
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		bearerToken(request).flatMap(accounts::authenticate).ifPresent(principal -> {
			var authority = new SimpleGrantedAuthority("ROLE_" + principal.role());
			SecurityContextHolder.getContext()
				.setAuthentication(UsernamePasswordAuthenticationToken.authenticated(principal, null, List.of(authority)));
		});
		chain.doFilter(request, response);
	}

	static Optional<String> bearerToken(HttpServletRequest request) {
		return bearerToken(request.getHeader(HttpHeaders.AUTHORIZATION));
	}

	static Optional<String> bearerToken(String header) {
		if (header == null || !header.regionMatches(true, 0, PREFIX, 0, PREFIX.length())) {
			return Optional.empty();
		}
		String token = header.substring(PREFIX.length()).strip();
		return token.isEmpty() ? Optional.empty() : Optional.of(token);
	}

}
