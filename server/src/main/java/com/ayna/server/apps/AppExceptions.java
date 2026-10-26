package com.ayna.server.apps;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

/** Errors of the applications API, mapped to HTTP status codes. */
final class AppExceptions {

	private AppExceptions() {
	}

	@ResponseStatus(HttpStatus.NOT_FOUND)
	static class AppNotFoundException extends RuntimeException {

		AppNotFoundException(String appId) {
			super("Application not found: " + appId);
		}

	}

	@ResponseStatus(HttpStatus.CONFLICT)
	static class DuplicateException extends RuntimeException {

		DuplicateException(String message) {
			super(message);
		}

	}

	@ResponseStatus(HttpStatus.BAD_REQUEST)
	static class InvalidRequestException extends RuntimeException {

		InvalidRequestException(String message) {
			super(message);
		}

	}

}
