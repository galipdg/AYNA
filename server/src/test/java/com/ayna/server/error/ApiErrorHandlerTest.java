package com.ayna.server.error;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;
import org.springframework.http.ProblemDetail;

import com.ayna.server.error.ApiExceptions.InvalidRequestException;

class ApiErrorHandlerTest {

	private final ApiErrorHandler handler = new ApiErrorHandler();

	@Test
	void listsEveryFieldErrorUpToTheCap() {
		ProblemDetail problem = handler.invalid(invalid(3));

		assertThat((List<?>) problem.getProperties().get("errors")).hasSize(3);
		assertThat(problem.getProperties()).containsEntry("errorCount", 3);
	}

	@Test
	void cutsFieldErrorsAtTheCapAndKeepsTheTotal() {
		ProblemDetail problem = handler.invalid(invalid(4231));

		List<?> errors = (List<?>) problem.getProperties().get("errors");
		assertThat(errors).hasSize(ApiErrorHandler.MAX_FIELD_ERRORS)
			.first()
			.isEqualTo(new FieldError("$.snapshot.elements[0].bounds", "bounds is required"));
		assertThat(problem.getProperties()).containsEntry("errorCount", 4231);
	}

	private static InvalidRequestException invalid(int count) {
		List<FieldError> errors = IntStream.range(0, count)
			.mapToObj(i -> new FieldError("$.snapshot.elements[" + i + "].bounds", "bounds is required"))
			.toList();
		return new InvalidRequestException("The snapshot is invalid", errors);
	}

}
