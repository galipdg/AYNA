package com.ayna.server.healing;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import org.springframework.stereotype.Component;

import com.ayna.server.error.FieldError;
import com.ayna.server.schema.SchemaFile;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * The healing proposal schema (`schemas/healing-proposal.schema.json`, 0.2) plus the arithmetic it
 * cannot express (ADR `2026-10-28-healing-proposal-transport`, "Exact numbers"). The rules and
 * their names are those of the reference check, `ai/tests/test_healing_proposal_schema.py`; every
 * arithmetic message starts with `[rule]`, so a client and the shared `cases.json` agree on it.
 */
@Component
public class HealingProposalSchema {

	private final SchemaFile file;

	public HealingProposalSchema(ObjectMapper mapper) {
		this.file = new SchemaFile(mapper, "schemas/healing-proposal.schema.json");
	}

	/** The one document version this schema accepts (`version` is a `const`). */
	public String version() {
		return file.version();
	}

	/** One entry per violation; empty when the document is valid. Arithmetic runs only on a schema-valid document. */
	public List<FieldError> validate(JsonNode document) {
		List<FieldError> errors = file.validate(document);
		return errors.isEmpty() ? arithmetic(document) : errors;
	}

	private static List<FieldError> arithmetic(JsonNode proposal) {
		List<FieldError> errors = new ArrayList<>();
		Map<String, Fraction> weights = exactMap(proposal.get("scorer").get("weights"), "$.scorer.weights", errors);
		JsonNode candidates = proposal.get("candidates");
		if (proposal.get("candidatesScored").intValue() < candidates.size()) {
			errors.add(error("$.candidatesScored", "candidatesScored", "fewer candidates scored than proposed"));
		}
		Set<String> elementIds = new HashSet<>();
		Set<String> compared = null;
		Fraction previousScore = null;
		String previousElement = null;
		for (int i = 0; i < candidates.size(); i++) {
			JsonNode candidate = candidates.get(i);
			String path = "$.candidates[" + i + "]";
			if (candidate.get("rank").intValue() != i + 1) {
				errors.add(error(path + ".rank", "ranks", "ranks must be 1, 2, 3 in order"));
			}
			String elementId = candidate.get("elementId").asString();
			if (!elementIds.add(elementId)) {
				errors.add(error(path + ".elementId", "uniqueElements", "element " + elementId + " is proposed twice"));
			}
			Fraction score = exact(candidate.get("score").asString(), path + ".score", errors);
			Map<String, Fraction> contributions = exactMap(candidate.get("contributions"), path + ".contributions", errors);
			Map<String, Fraction> similarities = exactMap(candidate.get("similarities"), path + ".similarities", errors);
			List<Fraction> values = new ArrayList<>();
			values.add(score);
			values.addAll(contributions.values());
			values.addAll(similarities.values());
			if (values.stream().anyMatch(v -> v.compareTo(Fraction.ONE) > 0)) {
				errors.add(error(path, "unitInterval", "scores, contributions and similarities lie in [0, 1]"));
			}
			if (!contributions.keySet().equals(similarities.keySet())) {
				errors.add(error(path + ".similarities", "sameKeys", "similarities and contributions name different properties"));
			}
			if (compared == null) {
				compared = similarities.keySet();
			}
			else if (!compared.equals(similarities.keySet())) {
				errors.add(error(path + ".similarities", "sameProperties",
						"every candidate is compared on the same properties as the first"));
			}
			if (similarities.keySet().stream().anyMatch(p -> weights.getOrDefault(p, Fraction.ZERO).isZero())) {
				errors.add(error(path + ".similarities", "weight", "a compared property has no weight in scorer.weights"));
			}
			Fraction total = similarities.keySet()
				.stream()
				.map(p -> weights.getOrDefault(p, Fraction.ZERO))
				.reduce(Fraction.ZERO, Fraction::plus);
			if (!total.isZero()) {
				for (Map.Entry<String, Fraction> similarity : similarities.entrySet()) {
					Fraction expected = weights.getOrDefault(similarity.getKey(), Fraction.ZERO)
						.times(similarity.getValue())
						.dividedBy(total);
					if (!expected.equals(contributions.get(similarity.getKey()))) {
						errors.add(error(path + ".contributions." + similarity.getKey(), "contribution",
								"should be weight × similarity / total weight = " + expected));
					}
				}
			}
			Fraction sum = contributions.values().stream().reduce(Fraction.ZERO, Fraction::plus);
			if (!sum.equals(score)) {
				errors.add(error(path + ".score", "sum", "the contributions add up to " + sum + ", not " + score));
			}
			if (previousScore != null && (score.compareTo(previousScore) > 0
					|| (score.equals(previousScore) && elementId.compareTo(previousElement) < 0))) {
				errors.add(error(path, "order", "candidates go by score descending, then elementId ascending"));
			}
			previousScore = score;
			previousElement = elementId;
		}
		return errors.stream().distinct().toList();
	}

	private static Map<String, Fraction> exactMap(JsonNode map, String path, List<FieldError> errors) {
		Map<String, Fraction> values = new LinkedHashMap<>();
		for (Map.Entry<String, JsonNode> entry : map.properties()) {
			values.put(entry.getKey(), exact(entry.getValue().asString(), path + "." + entry.getKey(), errors));
		}
		return values;
	}

	/** The schema's pattern has already checked the form; this checks lowest terms, as Python's `str(Fraction)` writes. */
	private static Fraction exact(String text, String path, List<FieldError> errors) {
		Fraction value = Fraction.parse(text);
		if (!value.toString().equals(text)) {
			errors.add(error(path, "lowestTerms", text + " is not in lowest terms; write " + value));
		}
		return value;
	}

	private static FieldError error(String path, String rule, String message) {
		return new FieldError(path, "[" + rule + "] " + message);
	}

	/** A non-negative exact rational in lowest terms. */
	record Fraction(BigInteger numerator, BigInteger denominator) implements Comparable<Fraction> {

		static final Fraction ZERO = new Fraction(BigInteger.ZERO, BigInteger.ONE);

		static final Fraction ONE = new Fraction(BigInteger.ONE, BigInteger.ONE);

		Fraction {
			Objects.requireNonNull(numerator);
			if (denominator.signum() <= 0) {
				throw new IllegalArgumentException("denominator must be positive");
			}
			BigInteger gcd = numerator.gcd(denominator);
			if (!gcd.equals(BigInteger.ONE) && gcd.signum() != 0) {
				numerator = numerator.divide(gcd);
				denominator = denominator.divide(gcd);
			}
			if (numerator.signum() == 0) {
				denominator = BigInteger.ONE;
			}
		}

		/** `"0"`, `"n"` or `"p/q"`; the form is the schema's to check. */
		static Fraction parse(String text) {
			int slash = text.indexOf('/');
			return slash < 0 ? new Fraction(new BigInteger(text), BigInteger.ONE)
					: new Fraction(new BigInteger(text.substring(0, slash)), new BigInteger(text.substring(slash + 1)));
		}

		Fraction plus(Fraction other) {
			return new Fraction(numerator.multiply(other.denominator).add(other.numerator.multiply(denominator)),
					denominator.multiply(other.denominator));
		}

		Fraction times(Fraction other) {
			return new Fraction(numerator.multiply(other.numerator), denominator.multiply(other.denominator));
		}

		Fraction dividedBy(Fraction other) {
			return new Fraction(numerator.multiply(other.denominator), denominator.multiply(other.numerator));
		}

		boolean isZero() {
			return numerator.signum() == 0;
		}

		/** For sorting only; never compared for equality (ADR, "Exact numbers"). */
		double toDouble() {
			return new java.math.BigDecimal(numerator).divide(new java.math.BigDecimal(denominator),
					java.math.MathContext.DECIMAL64).doubleValue();
		}

		@Override
		public int compareTo(Fraction other) {
			return numerator.multiply(other.denominator).compareTo(other.numerator.multiply(denominator));
		}

		@Override
		public String toString() {
			return denominator.equals(BigInteger.ONE) ? numerator.toString() : numerator + "/" + denominator;
		}

	}

}
