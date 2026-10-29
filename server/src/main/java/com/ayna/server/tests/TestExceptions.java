package com.ayna.server.tests;

import java.util.List;

import com.ayna.server.tests.StepSchema.FieldError;

/** Errors of the tests API; {@link TestErrorHandler} turns them into problem details. */
final class TestExceptions {

	private TestExceptions() {
	}

	static class NotFoundException extends RuntimeException {

		NotFoundException(String message) {
			super(message);
		}

	}

	static class DuplicateTestException extends RuntimeException {

		DuplicateTestException(String name) {
			super("A test with this name already exists in the application: " + name);
		}

	}

	/** A 400 that names every failing field of the request body. */
	static class InvalidRequestException extends RuntimeException {

		private final List<FieldError> errors;

		InvalidRequestException(String message, List<FieldError> errors) {
			super(message);
			this.errors = List.copyOf(errors);
		}

		InvalidRequestException(String path, String message) {
			this(message, List.of(new FieldError(path, message)));
		}

		List<FieldError> errors() {
			return errors;
		}

	}

}
