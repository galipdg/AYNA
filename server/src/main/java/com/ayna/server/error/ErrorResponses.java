package com.ayna.server.error;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import org.springframework.http.HttpStatus;

/**
 * The error statuses an endpoint can return; the OpenAPI contract lists them with the
 * problem-details body (#158). Only statuses {@code OpenApiConfig} defines a response for.
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ErrorResponses {

	HttpStatus[] value();

}
