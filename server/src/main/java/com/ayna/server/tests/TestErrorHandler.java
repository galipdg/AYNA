package com.ayna.server.tests;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.ayna.server.tests.TestExceptions.DuplicateTestException;
import com.ayna.server.tests.TestExceptions.InvalidRequestException;
import com.ayna.server.tests.TestExceptions.NotFoundException;

/**
 * Error bodies of the tests API as RFC 9457 problem details, so the message reaches the
 * client (NFR-15). A 400 also lists `errors: [{path, message}]`. Whether every API adopts
 * this shape is settled in #31.
 */
@RestControllerAdvice(basePackageClasses = TestController.class)
class TestErrorHandler {

	@ExceptionHandler
	ProblemDetail notFound(NotFoundException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail duplicate(DuplicateTestException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail invalid(InvalidRequestException ex) {
		ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());
		problem.setProperty("errors", ex.errors());
		return problem;
	}

}
