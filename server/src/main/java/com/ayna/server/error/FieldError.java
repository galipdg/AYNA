package com.ayna.server.error;

/** One failing field of a request body; `path` is a JSON path into it, e.g. `$.steps[2].value`. */
public record FieldError(String path, String message) {
}
