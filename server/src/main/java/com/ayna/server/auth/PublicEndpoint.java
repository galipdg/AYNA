package com.ayna.server.auth;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks an endpoint that needs no account, so the OpenAPI contract shows it without
 * `bearerAuth` and without a 401. The rule itself is in {@code SecurityConfig}; keep the two
 * in step (`AuthIntegrationTest` checks it).
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface PublicEndpoint {

}
