package com.ayna.server.apps;

/** Request and response bodies of the applications API. */
final class AppDtos {

	private AppDtos() {
	}

	record CreateAppRequest(String name, String technology) {
	}

	record AppResponse(String id, String name, String technology) {
	}

	record CreateVersionRequest(String version) {
	}

	record VersionResponse(String id, String version) {
	}

}
