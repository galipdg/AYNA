package com.ayna.server.error;

/**
 * One failing field of a request body; `path` is a JSONPath (RFC 9535) into it with member
 * names and array indices only, e.g. `$.steps[2].value`; never a filter or wildcard.
 */
public record FieldError(String path, String message) {
}
