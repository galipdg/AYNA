package com.ayna.server.auth;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AnonymousAuthenticationFilter;
import tools.jackson.databind.ObjectMapper;

/**
 * Who may call what (ADR accounts-and-tokens, NFR-32). Public: login, health and the API
 * docs. Admins only: accounts and API tokens. Everything else under `/api/**` needs any
 * account. No cookies and no server-side HTTP session, so there is nothing for CSRF to use.
 */
@Configuration(proxyBeanMethods = false)
class SecurityConfig {

	/** BCrypt cost 10 (Spring's default), about 0.1 s per check. */
	@Bean
	PasswordEncoder passwordEncoder() {
		return new BCryptPasswordEncoder(10);
	}

	@Bean
	SecurityFilterChain apiSecurity(HttpSecurity http, AccountService accounts, ObjectMapper mapper) throws Exception {
		return http.csrf(csrf -> csrf.disable())
			.httpBasic(basic -> basic.disable())
			.formLogin(form -> form.disable())
			.logout(logout -> logout.disable())
			.requestCache(cache -> cache.disable())
			.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
			.addFilterBefore(new BearerTokenFilter(accounts), AnonymousAuthenticationFilter.class)
			.authorizeHttpRequests(auth -> auth
				.requestMatchers(HttpMethod.POST, "/api/auth/login").permitAll()
				.requestMatchers(HttpMethod.GET, "/api/health").permitAll()
				.requestMatchers("/v3/api-docs/**", "/v3/api-docs.yaml", "/swagger-ui.html", "/swagger-ui/**").permitAll()
				.requestMatchers("/api/users/**", "/api/tokens/**").hasRole(AynaPrincipal.ADMIN)
				.anyRequest().authenticated())
			.exceptionHandling(errors -> errors
				.authenticationEntryPoint((request, response, ex) -> problem(mapper, request, response,
						HttpStatus.UNAUTHORIZED, "Log in first: the request has no valid session or API token"))
				.accessDeniedHandler((request, response, ex) -> problem(mapper, request, response,
						HttpStatus.FORBIDDEN, "Only admins may do this")))
			.build();
	}

	/** The same RFC 9457 body as `ApiErrorHandler`; these errors happen before any controller runs. */
	private static void problem(ObjectMapper mapper, HttpServletRequest request, HttpServletResponse response,
			HttpStatus status, String detail) throws IOException {
		Map<String, Object> body = new LinkedHashMap<>();
		body.put("title", status.getReasonPhrase());
		body.put("status", status.value());
		body.put("detail", detail);
		body.put("instance", request.getRequestURI());
		response.setStatus(status.value());
		response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
		if (status == HttpStatus.UNAUTHORIZED) {
			response.setHeader("WWW-Authenticate", "Bearer");
		}
		mapper.writeValue(response.getOutputStream(), body);
	}

}
