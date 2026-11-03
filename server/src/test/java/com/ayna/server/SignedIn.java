package com.ayna.server;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import java.util.List;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.MockMvcBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import com.ayna.server.auth.AynaPrincipal;

/**
 * Sends every MockMvc request as a tester, for tests of APIs other than accounts (#60).
 * The account is not in the database, so `createdBy.username` is null in those tests;
 * `AuthIntegrationTest` covers real logins and tokens.
 */
@TestConfiguration(proxyBeanMethods = false)
public class SignedIn {

	public static final AynaPrincipal TESTER = new AynaPrincipal("00000000-0000-4000-8000-000000000001", "tester",
			AynaPrincipal.TESTER);

	@Bean
	MockMvcBuilderCustomizer signedInAsTester() {
		var auth = UsernamePasswordAuthenticationToken.authenticated(TESTER, null,
				List.of(new SimpleGrantedAuthority("ROLE_" + TESTER.role())));
		return builder -> builder.defaultRequest(get("/").with(authentication(auth)));
	}

}
