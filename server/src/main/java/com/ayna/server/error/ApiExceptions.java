package com.ayna.server.error;

import java.util.List;

/**
 * Errors every API throws; {@link ApiErrorHandler} turns them into RFC 9457 problem details.
 * The message becomes the `detail` the client shows, so it names what it concerns (NFR-15).
 */
public final class ApiExceptions {

	private ApiExceptions() {
	}

	/** 401: the login failed; a missing or invalid token is answered by the security chain. */
	public static class UnauthorizedException extends RuntimeException {

		public UnauthorizedException(String message) {
			super(message);
		}

	}

	/** 404: an id in the path names nothing. */
	public static class NotFoundException extends RuntimeException {

		public NotFoundException(String message) {
			super(message);
		}

	}

	/** 409: the request breaks a uniqueness rule, such as a duplicate name. */
	public static class ConflictException extends RuntimeException {

		public ConflictException(String message) {
			super(message);
		}

	}

	/** 400 that names every failing field of the request body. */
	public static class InvalidRequestException extends RuntimeException {

		private final List<FieldError> errors;

		public InvalidRequestException(String message, List<FieldError> errors) {
			super(message);
			this.errors = List.copyOf(errors);
		}

		public InvalidRequestException(String path, String message) {
			this(message, List.of(new FieldError(path, message)));
		}

		public List<FieldError> errors() {
			return errors;
		}

	}

}
