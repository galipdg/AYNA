package com.ayna.server.auth;

/**
 * The account a request acts for, set by {@link BearerTokenFilter}. Controllers take it with
 * {@code @AuthenticationPrincipal} and pass {@link #userId()} to whatever they write (who did it).
 */
public record AynaPrincipal(String userId, String username, String role) {

	public static final String ADMIN = "admin";

	public static final String TESTER = "tester";

	public boolean isAdmin() {
		return ADMIN.equals(role);
	}

}
