package com.ayna.server.error;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import com.ayna.server.error.ApiExceptions.ConflictException;
import com.ayna.server.error.ApiExceptions.InvalidRequestException;
import com.ayna.server.error.ApiExceptions.NotFoundException;
import com.ayna.server.error.ApiExceptions.TooLargeException;
import com.ayna.server.error.ApiExceptions.UnauthorizedException;

/**
 * One error body for every API (#158): RFC 9457 problem details, so the message reaches the
 * client (NFR-15). A validation 400 also lists `errors: [{path, message}]` and their total in
 * `errorCount`. The base class gives Spring's own errors (unreadable JSON, unknown path, wrong
 * method) the same shape.
 */
@RestControllerAdvice
class ApiErrorHandler extends ResponseEntityExceptionHandler {

	/** A large invalid body (a window snapshot) must not get an even larger error body. */
	static final int MAX_FIELD_ERRORS = 50;

	@ExceptionHandler
	ProblemDetail unauthorized(UnauthorizedException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.UNAUTHORIZED, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail notFound(NotFoundException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail conflict(ConflictException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail tooLarge(TooLargeException ex) {
		return ProblemDetail.forStatusAndDetail(HttpStatus.CONTENT_TOO_LARGE, ex.getMessage());
	}

	@ExceptionHandler
	ProblemDetail invalid(InvalidRequestException ex) {
		ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());
		List<FieldError> errors = ex.errors();
		problem.setProperty("errors", errors.subList(0, Math.min(errors.size(), MAX_FIELD_ERRORS)));
		problem.setProperty("errorCount", errors.size());
		return problem;
	}

}
