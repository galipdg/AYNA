package com.ayna.server.auth;

/**
 * Who did something, as responses show it (`createdBy`, `updatedBy`, later `startedBy` and
 * `decidedBy`). The node stores only the user id; a removed account still has its name.
 */
public record UserRef(String id, String username) {

}
