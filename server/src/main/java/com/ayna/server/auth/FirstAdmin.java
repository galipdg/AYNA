package com.ayna.server.auth;

import java.util.Locale;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * Creates the first admin from `AYNA_ADMIN_USERNAME` and `AYNA_ADMIN_PASSWORD` when the
 * database has no active admin (ADR accounts-and-tokens). Ignored once an admin exists.
 */
@Component
class FirstAdmin implements ApplicationRunner {

	private static final Logger log = LoggerFactory.getLogger(FirstAdmin.class);

	private final AccountService accounts;

	private final String username;

	private final String password;

	FirstAdmin(AccountService accounts, @Value("${ayna.admin.username:}") String username,
			@Value("${ayna.admin.password:}") String password) {
		this.accounts = accounts;
		this.username = username;
		this.password = password;
	}

	@Override
	public void run(ApplicationArguments args) {
		if (username.isBlank() || password.isBlank()) {
			if (accounts.listUsers().stream().noneMatch(u -> AynaPrincipal.ADMIN.equals(u.role()))) {
				log.warn("No admin account exists and AYNA_ADMIN_USERNAME / AYNA_ADMIN_PASSWORD are not set: "
						+ "nobody can log in");
			}
			return;
		}
		if (accounts.createFirstAdmin(username, password)) {
			log.info("Created the first admin account '{}'", username.strip().toLowerCase(Locale.ROOT));
		}
	}

}
