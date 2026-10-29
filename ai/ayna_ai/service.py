"""HTTP service: a Turkish instruction -> suggested steps, each with a reason (#71).

    POST /ai/generate-steps   retrieval -> constrained generation -> validation
    GET  /ai/health           does the model server answer and have the model?

The caller is the AYNA server (#78 chat panel); the contract is `ai/API.md`.
The service listens on loopback unless started with --allow-remote, and talks
only to a loopback model server (`ayna_ai.ollama`), so it works on a closed
network. Every step in a response's `steps` targets an object the retriever
returned for that request: the generator constrains and checks it, and the
service checks it once more before answering. A generated step that fails
either check is not suggested; it is listed in `dropped` with the reason.

From `ai/`, with `ollama serve` running:

    python -m ayna_ai.service --port 8090 --model qwen3:8b
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import socket
import socketserver
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jsonschema import Draft202012Validator

from ayna_ai import __version__
from ayna_ai.generate import (
    GenerationResult,
    GenerationSettings,
    Status,
    StepGenerator,
)
from ayna_ai.ollama import DEFAULT_HOST, ModelServerError, OllamaClient
from ayna_ai.retrieve import (
    PassThroughRetriever,
    RetrievalInputError,
    RetrievalQuery,
    Retriever,
)
from ayna_ai.validate import NO_MATCH, DroppedStep, StepValidator

log = logging.getLogger(__name__)

DEFAULT_PORT = 8090  # AYNA_AI_URL in .env.example
GENERATE_PATH = "/ai/generate-steps"
HEALTH_PATH = "/ai/health"
MAX_TEXT = 2000  # characters of instruction
MAX_OBJECTS = 100  # keeps the prompt well inside num_ctx 4096 (~8-20 tokens each)
DRAIN_LIMIT = 1024 * 1024  # an oversized body is read up to this, then dropped
MAX_DETAILS = 20

# Generator failure -> HTTP status and a message for people.
FAILURES: dict[Status, tuple[int, str]] = {
    Status.INVALID_JSON: (422, "the model's answer is not valid JSON"),
    Status.TRUNCATED: (422, "the model's answer was cut off at the output limit"),
    Status.INVALID_SCHEMA: (422, "the model's answer is not a step document"),
    Status.NO_VALID_STEPS: (
        422,
        "the description could not be turned into valid steps",
    ),
    Status.TIMEOUT: (504, "no answer within the service timeout"),
    Status.SERVER_ERROR: (503, "the model server is unavailable"),
}


def request_schema(step_schema: dict) -> dict:
    """JSON schema of a generate-steps request; object names follow the step schema."""
    return {
        "$defs": step_schema["$defs"],
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_TEXT,
                "pattern": r"\S",
            },
            "app": {"type": "string", "minLength": 1, "maxLength": 200},
            "version": {"type": "string", "maxLength": 100},
            "screen": {"type": "string", "maxLength": 200},
            "objects": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_OBJECTS,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"$ref": "#/$defs/logicalName"},
                        "description": {"type": "string", "maxLength": 200},
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
            "model": {"type": "string", "minLength": 1, "maxLength": 100},
        },
        "required": ["text", "app"],
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class ServiceConfig:
    models: tuple[str, ...] = (GenerationSettings.model,)  # the first is the default
    model_host: str = DEFAULT_HOST
    # One request end to end: retrieval and the model call, a cold model load
    # included. Well below the batch CLI's 120 s, so the panel gets a 504
    # instead of hanging: ~3x the idle p95 of #37, above the 25 s p95 measured
    # under heavy load (#71 task note).
    timeout_s: float = 30.0
    health_timeout_s: float = 2.0
    max_body_bytes: int = 64 * 1024
    num_predict: int = 768  # reasons add ~15-25 output tokens per step


class RequestError(Exception):
    """A request the service cannot serve; becomes an error response."""

    def __init__(self, code: int, status: str, error: str, details=()) -> None:
        super().__init__(error)
        self.code, self.status, self.error = code, status, error
        self.details = [_short(d) for d in list(details)[:MAX_DETAILS]]

    def body(self) -> dict:
        body = {"status": self.status, "error": self.error}
        if self.details:
            body["details"] = self.details
        return body


class StepService:
    """Request -> response, without HTTP: validate, retrieve, generate, guard."""

    def __init__(
        self,
        config: ServiceConfig | None = None,
        *,
        retriever: Retriever | None = None,
        client=None,
        health_client: OllamaClient | None = None,
        step_schema: dict | None = None,
    ) -> None:
        self.config = config or ServiceConfig()
        if not self.config.models:
            raise ValueError("the service needs at least one model")
        self.retriever = retriever or PassThroughRetriever()
        if client is None:
            client = OllamaClient(self.config.model_host, self.config.timeout_s)
        self.health_client = health_client or OllamaClient(
            self.config.model_host, self.config.health_timeout_s
        )
        self.validator = StepValidator(step_schema)
        self.generators = {
            model: StepGenerator(
                client,
                GenerationSettings(
                    model=model, reasons=True, num_predict=self.config.num_predict
                ),
                self.validator.schema,
            )
            for model in self.config.models
        }
        default = self.generators[self.default_model]
        self.prompt_version = default.prompt_version
        self.schema_version = default.version
        self._requests = Draft202012Validator(request_schema(self.validator.schema))

    @property
    def default_model(self) -> str:
        return self.config.models[0]

    def warm_up(self) -> None:
        """Load the default model so the first request does not pay for it."""
        try:
            self.generators[self.default_model].warm_up()
        except ModelServerError as exc:
            log.warning(_record("warmup_failed", model=self.default_model, error=exc))
        else:
            log.info(_record("warmup", model=self.default_model))

    def generate_steps(self, payload: object) -> tuple[int, dict]:
        """(HTTP status, response body) for a parsed JSON request body."""
        started = time.perf_counter()
        try:
            code, body = self._generate(payload)
        except RequestError as exc:
            code, body = exc.code, exc.body()
        body["latencyMs"] = round((time.perf_counter() - started) * 1000)
        return code, body

    def _generate(self, payload: object) -> tuple[int, dict]:
        deadline = time.monotonic() + self.config.timeout_s
        query, model = self._parse(payload)
        try:
            objects = self.retriever.retrieve(query)
        except RetrievalInputError as exc:
            raise RequestError(400, "bad_request", str(exc)) from exc
        if not objects:
            raise RequestError(
                422, "no_objects", "no repository objects found for this request"
            )

        left = deadline - time.monotonic()
        if left > 0:
            result = self.generators[model].generate(
                query.text, objects, timeout_s=left
            )
        else:
            result = GenerationResult(Status.TIMEOUT)
        if result.status is Status.TIMEOUT:
            result.errors = [f"no answer within {self.config.timeout_s:g} s"]
        if result.ok:
            self._guard(result, objects, model)

        body = {"status": str(result.status), "model": model}
        if result.ok:
            code = 200
            body["steps"] = [
                {**step, "reason": reason}
                for step, reason in zip(
                    result.document["steps"], result.reasons, strict=True
                )
            ]
        else:
            code, body["error"] = FAILURES[result.status]
            body["details"] = [_short(e) for e in result.errors[:MAX_DETAILS]]
            if result.status is Status.NO_VALID_STEPS:
                body["steps"] = []
        if result.ok or result.status is Status.NO_VALID_STEPS:
            body["dropped"] = [d.to_dict() for d in result.dropped]
        body["schemaVersion"] = self.schema_version
        body["promptVersion"] = self.prompt_version
        return code, body

    def _guard(self, result: GenerationResult, objects, model: str) -> None:
        """Re-check every kept step against `objects`; move any that fail to dropped.

        The generator constrains and checks targets already; this is the last
        line before the caller, so a bug there cannot leak a step.
        """
        dropped_at = {d.index for d in result.dropped}
        total = len(result.document["steps"]) + len(dropped_at)
        kept_at = [i for i in range(total) if i not in dropped_at]
        steps, reasons, leaks = [], [], []
        for index, step, reason in zip(
            kept_at, result.document["steps"], result.reasons, strict=True
        ):
            problems = self.validator.step_problems(step, objects)
            if problems:
                leaks.append(
                    DroppedStep.of(index, {**step, "reason": reason}, problems)
                )
            else:
                steps.append(step)
                reasons.append(reason)
        if not leaks:
            return
        # Index and code only: a reason may quote a step value (test data).
        caught = [f"{d.index}:{d.code}" for d in leaks]
        log.error(_record("target_guard", model=model, dropped=caught))
        result.dropped = sorted([*result.dropped, *leaks], key=lambda d: d.index)
        if steps:
            result.document = {**result.document, "steps": steps}
            result.reasons = reasons
            return
        result.status = Status.NO_VALID_STEPS
        result.document = result.reasons = None
        result.errors = [f"$.steps[{d.index}]: {d.reason}" for d in result.dropped]

    def _parse(self, payload: object) -> tuple[RetrievalQuery, str]:
        errors = sorted(self._requests.iter_errors(payload), key=lambda e: e.json_path)
        if errors:
            raise RequestError(
                400,
                "bad_request",
                "the request does not fit the generate-steps contract (ai/API.md)",
                [f"{e.json_path}: {e.message}" for e in errors],
            )
        objects = None
        if "objects" in payload:
            names = [obj["name"] for obj in payload["objects"]]
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                raise RequestError(
                    400, "bad_request", "duplicate object names", duplicates
                )
            if NO_MATCH in names:
                raise RequestError(
                    400,
                    "bad_request",
                    f"the object name {NO_MATCH!r} is reserved: it means "
                    "'no repository object matches'",
                )
            objects = {o["name"]: o.get("description", "") for o in payload["objects"]}
        model = payload.get("model", self.default_model)
        if model not in self.generators:
            raise RequestError(
                400,
                "bad_request",
                f"model {model!r} is not offered by this service",
                [f"offered: {', '.join(self.generators)}"],
            )
        query = RetrievalQuery(
            text=payload["text"],
            app=payload["app"],
            version=payload.get("version"),
            screen=payload.get("screen"),
            objects=objects,
        )
        return query, model

    def health(self) -> dict:
        """Whether generation can work now: model server up, default model pulled."""
        error = None
        try:
            pulled = self.health_client.models()
        except ModelServerError as exc:
            pulled, error = None, str(exc)
        models = [
            {"name": m, "available": pulled is not None and _has_model(pulled, m)}
            for m in self.config.models
        ]
        ready = pulled is not None and models[0]["available"]
        if ready:
            status = "ok"
        elif pulled is None:
            status = "model_server_down"
        else:
            status = "model_missing"
        body = {
            "status": status,
            "ready": ready,
            "modelServer": {
                "url": self.health_client.host,
                "reachable": pulled is not None,
            },
            "defaultModel": self.default_model,
            "models": models,
            "schemaVersion": self.schema_version,
            "promptVersion": self.prompt_version,
            "serviceVersion": __version__,
        }
        if error:
            body["error"] = error
        return body


def _has_model(pulled: Sequence[str], model: str) -> bool:
    """Ollama lists an untagged pull as `name:latest`."""
    return model in pulled or (":" not in model and f"{model}:latest" in pulled)


def _too_large(limit: int) -> RequestError:
    return RequestError(413, "too_large", f"the request body is over {limit} bytes")


def _short(text: object, limit: int = 300) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _record(event: str, **fields) -> str:
    """One JSON log line."""
    ts = datetime.now().astimezone().isoformat(timespec="milliseconds")
    return json.dumps({"ts": ts, "event": event, **fields}, default=str)


# --- HTTP ---------------------------------------------------------------------


def is_loopback_host(host: str) -> bool:
    """True for localhost and loopback IP addresses (127.0.0.0/8, ::1)."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ServiceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: StepService) -> None:
        self.address_family = socket.AF_INET6 if ":" in address[0] else socket.AF_INET
        self.service = service
        super().__init__(address, ServiceHandler)

    def server_bind(self) -> None:
        # HTTPServer.server_bind does a reverse DNS lookup (getfqdn), which can
        # take half a minute on a machine without a resolver (closed network).
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


class ServiceHandler(BaseHTTPRequestHandler):
    server: ServiceServer
    server_version = f"ayna-ai/{__version__}"
    sys_version = ""
    timeout = 30  # seconds to receive a request (generation is not limited by it)

    def parse_request(self) -> bool:
        self._started = time.perf_counter()
        return super().parse_request()

    def do_GET(self) -> None:
        path = self._route()
        if path == HEALTH_PATH:
            self._send(200, self.server.service.health())
        elif path == GENERATE_PATH:
            self._wrong_method("POST")
        else:
            self._not_found()

    def do_POST(self) -> None:
        path = self._route()
        if path != GENERATE_PATH:
            self._discard_body()
            if path == HEALTH_PATH:
                self._wrong_method("GET")
            else:
                self._not_found()
            return
        try:
            code, body = self.server.service.generate_steps(self._read_json())
        except RequestError as exc:
            code, body = exc.code, exc.body()
        except Exception:  # a bug: answer 500 instead of dropping the connection
            log.exception(_record("internal_error", path=path))
            code, body = 500, {"status": "internal_error", "error": "internal error"}
        self._send(code, body)

    def _other_method(self) -> None:
        self._discard_body()
        path = self._route()
        if path == GENERATE_PATH:
            self._wrong_method("POST")
        elif path == HEALTH_PATH:
            self._wrong_method("GET")
        else:
            self._not_found()

    do_PUT = do_PATCH = do_DELETE = _other_method

    def _read_json(self) -> object:
        data = self._read_body(self.server.service.config.max_body_bytes)
        if self.headers.get_content_type() != "application/json":
            raise RequestError(
                415, "unsupported_media_type", "Content-Type must be application/json"
            )
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(
                400, "bad_request", "the body is not UTF-8 JSON", [exc]
            ) from exc

    def _read_body(self, limit: int) -> bytes:
        """The request body: Content-Length or chunked (JDK HttpClient may send it)."""
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            return self._read_chunked(limit)
        header = self.headers.get("Content-Length")
        if header is None:
            raise RequestError(
                411, "length_required", "send Content-Length or a chunked body"
            )
        if not header.strip().isdigit():
            raise RequestError(400, "bad_request", "invalid Content-Length")
        length = int(header)
        if length > limit:
            self._discard(length)
            raise _too_large(limit)
        data = self.rfile.read(length)
        if len(data) < length:
            raise RequestError(400, "bad_request", "the body ended early")
        return data

    def _read_chunked(self, limit: int) -> bytes:
        data, total = bytearray(), 0
        try:
            while True:
                size = int(self.rfile.readline(1024).split(b";", 1)[0], 16)
                if size < 0:
                    raise ValueError("negative chunk size")
                if size == 0:
                    break
                total += size
                if total > DRAIN_LIMIT:
                    raise _too_large(limit)
                chunk = self.rfile.read(size)
                if len(chunk) < size or self.rfile.readline(1024).strip():
                    raise ValueError("chunk shorter than its size")
                if total <= limit:
                    data += chunk
            while self.rfile.readline(1024).strip():
                pass  # trailer fields
        except ValueError as exc:
            raise RequestError(400, "bad_request", "invalid chunked body") from exc
        if total > limit:
            raise _too_large(limit)
        return bytes(data)

    def _route(self) -> str:
        return self.path.split("?", 1)[0]

    def _discard_body(self) -> None:
        header = self.headers.get("Content-Length")
        if header and header.isdigit():
            self._discard(int(header))

    def _discard(self, length: int) -> None:
        """Read and drop a body: closing with unread data resets the connection,
        and the client could lose the error response."""
        left = min(length, DRAIN_LIMIT)
        try:
            while left > 0:
                chunk = self.rfile.read(min(left, 64 * 1024))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def _wrong_method(self, allowed: str) -> None:
        self._send(
            405,
            {"status": "method_not_allowed", "error": f"use {allowed}"},
            {"Allow": allowed},
        )

    def _not_found(self) -> None:
        self._send(
            404,
            {
                "status": "not_found",
                "error": f"no such path; use {GENERATE_PATH} or {HEALTH_PATH}",
            },
        )

    def _send(self, code: int, body: dict, headers: dict | None = None) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            log.warning(_record("client_gone", path=self._route(), code=code))
        # The instruction text is test data and may hold passwords: not logged.
        log.info(
            _record(
                "request",
                method=self.command,
                path=self._route(),
                code=code,
                status=body.get("status"),
                model=body.get("model"),
                steps=len(body["steps"]) if "steps" in body else None,
                dropped=len(body["dropped"]) if "dropped" in body else None,
                latency_ms=round((time.perf_counter() - self._started) * 1000),
            )
        )

    def log_message(self, format: str, *args) -> None:
        # Only http.server's own errors (bad request line, ...) arrive here; the
        # per-request JSON line is written by _send.
        log.warning(_record("http", message=format % args))

    def log_request(self, code="-", size="-") -> None:
        pass


def create_server(
    service: StepService,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    *,
    allow_remote: bool = False,
) -> ServiceServer:
    """Bind the service; a non-loopback `host` needs `allow_remote` and is logged."""
    if not is_loopback_host(host):
        if not allow_remote:
            raise ValueError(
                f"refusing to listen on {host!r}: not a loopback address (closed "
                "network). Pass --allow-remote to expose the service, e.g. in a container."
            )
        log.warning(
            _record(
                "remote_bind",
                host=host,
                port=port,
                message="listening on a non-loopback address: reachable from other machines",
            )
        )
    return ServiceServer((host, port), service)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ayna_ai.service",
        description="Serve POST /ai/generate-steps and GET /ai/health (ai/API.md).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to listen on; must be loopback unless --allow-remote",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="allow a non-loopback --host (e.g. 0.0.0.0 in a container); logged",
    )
    parser.add_argument(
        "--model",
        action="append",
        help=f"model to offer, repeatable; the first is the default "
        f"(default: {GenerationSettings.model})",
    )
    parser.add_argument(
        "--model-host", default=DEFAULT_HOST, help="loopback Ollama URL"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=ServiceConfig.timeout_s,
        help="seconds per request, retrieval and model call; 504 when exceeded",
    )
    parser.add_argument(
        "--max-body-bytes", type=int, default=ServiceConfig.max_body_bytes
    )
    parser.add_argument(
        "--warmup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="load the default model at start (in the background)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    models = tuple(dict.fromkeys(args.model or [GenerationSettings.model]))
    config = ServiceConfig(
        models=models,
        model_host=args.model_host,
        timeout_s=args.timeout,
        max_body_bytes=args.max_body_bytes,
    )
    try:
        service = StepService(config)
        server = create_server(
            service, args.host, args.port, allow_remote=args.allow_remote
        )
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        print(f"cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 1

    host, port = server.server_address[:2]
    log.info(
        _record(
            "start",
            url=f"http://{host}:{port}",
            models=list(models),
            model_host=config.model_host,
            timeout_s=config.timeout_s,
            prompt_version=service.prompt_version,
        )
    )
    if args.warmup:
        threading.Thread(target=service.warm_up, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log.info(_record("stop"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
