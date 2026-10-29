"""Turkish test instructions -> step documents with schema-constrained decoding (#37).

For every request the generator derives a JSON schema from
`schemas/step.schema.json`, narrows it to the repository objects the caller
passes in and gives it to a local Ollama server as the `format` of /api/chat,
so the decoder can only emit text that fits it. The answer is then validated
against the original step schema and the object list. Anything else comes back
as a typed failure (`Status`), never as steps.

Batch run, from `ai/` (results JSON, one JSON log line per scenario):

    python -m ayna_ai.generate --input spikes/llm-smoke-inputs.jsonl \\
        --objects tests/data/spike-objects.json --model qwen3:8b --out results.json
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import platform
import statistics
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from jsonschema import Draft202012Validator

from ayna_ai.ollama import DEFAULT_HOST, ModelServerError, ModelTimeout, OllamaClient
from ayna_ai.validate import StepValidator, load_step_schema

log = logging.getLogger(__name__)

# --- Generation schema --------------------------------------------------------

ANNOTATIONS = frozenset(
    {"$schema", "$id", "$comment", "title", "description", "examples", "default"}
)
# What the derivation understands on an object schema. Anything else raises,
# so a change to the step schema cannot silently loosen generation.
OBJECT_KEYWORDS = frozenset(
    {"type", "properties", "required", "additionalProperties", "allOf"}
)
ARRAY_KEYWORDS = frozenset({"type", "items", "minItems", "maxItems"})
# Grammar converters (llama.cpp's json-schema-to-grammar, used by Ollama) do
# not implement these; none may be left in the derived schema.
NOT_FOR_GRAMMAR = frozenset(
    [
        "$ref",
        "$defs",
        "allOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "dependentRequired",
    ]
)
SERVER_FIELDS = ("id",)  # assigned by the server on save, never generated


class SchemaDerivationError(ValueError):
    """The step schema uses a construct the derivation does not handle."""


def generation_schema(
    step_schema: dict,
    objects: Sequence[str],
    *,
    max_steps: int = 12,
    max_text: int = 200,
) -> dict:
    """JSON schema for constrained decoding, derived from the step schema.

    It accepts a subset of what the step schema accepts:
    - each keyword becomes one `anyOf` branch holding only the fields its
      `if`/`then` rule allows (grammar converters ignore `if`/`then`); the
      checkpoint is split the same way by `property`;
    - `target` is an `enum` of `objects`;
    - free strings get `maxLength <= max_text` and the list 1..`max_steps`
      steps, so a runaway output ends early (#7 finding 1);
    - server-assigned fields (`id`) are left out.
    Local `$ref`s are inlined and annotations dropped.
    """
    names = list(dict.fromkeys(objects))
    if not names:
        raise ValueError("generation needs at least one repository object")
    root = _inline(step_schema, step_schema)
    _check_keys(root, OBJECT_KEYWORDS - {"allOf"}, "root")
    steps = root["properties"]["steps"]
    _check_keys(steps, ARRAY_KEYWORDS, "steps")
    step = steps["items"]
    _check_target_names(step["properties"]["target"], names)

    variants = []
    for variant in _variants(step, "keyword", "step"):
        props = variant["properties"]
        for name in SERVER_FIELDS:
            if name in variant["required"]:
                raise SchemaDerivationError(f"step: server field {name!r} is required")
            props.pop(name, None)
        props["target"] = {"type": "string", "enum": names}
        if "checkpoint" in props:
            props["checkpoint"] = _any_of(
                _variants(props["checkpoint"], "property", "checkpoint")
            )
        variants.append(variant)

    derived = {
        "type": "object",
        "properties": {
            **root["properties"],
            "steps": {
                "type": "array",
                "items": _any_of(variants),
                "minItems": max(steps.get("minItems", 0), 1),
                "maxItems": min(steps.get("maxItems", max_steps), max_steps),
            },
        },
        "required": root["required"],
        "additionalProperties": False,
    }
    _cap_strings(derived, max_text)
    _check_grammar_friendly(derived, "$")
    return derived


def _inline(schema: object, root: dict) -> object:
    """Copy of `schema` with local `$ref`s resolved and annotations removed."""
    if not isinstance(schema, dict):
        return schema  # boolean subschema
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise SchemaDerivationError(f"only local $refs are supported: {ref}")
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        rest = {k: v for k, v in schema.items() if k != "$ref"}
        return _inline({**target, **rest}, root)
    out = {}
    for key, value in schema.items():
        if key in ANNOTATIONS or key == "$defs":
            continue
        if key == "properties":
            out[key] = {name: _inline(sub, root) for name, sub in value.items()}
        elif key in ("allOf", "anyOf", "oneOf"):
            out[key] = [_inline(sub, root) for sub in value]
        elif key in ("items", "if", "then", "else", "not", "additionalProperties"):
            out[key] = _inline(value, root)
        else:
            out[key] = value
    return out


def _variants(obj: dict, key: str, where: str) -> list[dict]:
    """Rewrite `allOf: [{if: <key> is X, then: ...}, ...]` as one schema per group.

    Values of `key` to which the same rules apply share a variant.
    """
    _check_keys(obj, OBJECT_KEYWORDS, where)
    if key not in obj.get("required", []):
        raise SchemaDerivationError(f"{where}: the selector {key!r} must be required")
    selector = obj["properties"][key]
    values = selector["enum"] if "enum" in selector else [selector["const"]]
    rules = [_rule(rule, key, where) for rule in obj.get("allOf", [])]

    groups: dict[tuple[int, ...], list] = {}
    for value in values:
        applied = tuple(i for i, (when, _) in enumerate(rules) if value in when)
        groups.setdefault(applied, []).append(value)

    variants = []
    for applied, group in groups.items():
        props = copy.deepcopy(obj["properties"])
        required = list(obj["required"])
        for i in applied:
            then = rules[i][1]
            for name, sub in then.get("properties", {}).items():
                if sub is False:
                    props.pop(name, None)
                elif name in props:
                    props[name] = _intersect(props[name], sub, f"{where}.{name}")
            required += [
                name for name in then.get("required", []) if name not in required
            ]
        props[key] = {"const": group[0]} if len(group) == 1 else {"enum": group}
        missing = [name for name in required if name not in props]
        if missing:
            raise SchemaDerivationError(
                f"{where} {group}: required but not allowed: {missing}"
            )
        variants.append(
            {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            }
        )
    return variants


def _rule(rule: dict, key: str, where: str) -> tuple[list, dict]:
    """(values of `key` the rule applies to, its `then`) for `if <key> is X then ...`."""
    if not isinstance(rule, dict) or set(rule) != {"if", "then"}:
        raise SchemaDerivationError(f"{where}: allOf entries must be if/then rules")
    cond, then = rule["if"], rule["then"]
    if set(cond) - {"required", "properties"} or set(cond.get("properties", {})) != {
        key
    }:
        raise SchemaDerivationError(f"{where}: if must test only {key!r}")
    test = cond["properties"][key]
    if set(test) == {"const"}:
        when = [test["const"]]
    elif set(test) == {"enum"}:
        when = list(test["enum"])
    else:
        raise SchemaDerivationError(f"{where}: if must use const or enum on {key!r}")
    if not isinstance(then, dict) or set(then) - {"properties", "required"}:
        raise SchemaDerivationError(
            f"{where}: then may only set properties and required"
        )
    return when, then


def _intersect(base: dict, extra: dict, where: str) -> dict:
    """A schema that both `base` and `extra` accept (for the keywords used in v0)."""
    merged = dict(base)
    for key, value in extra.items():
        if key not in merged:
            merged[key] = value
        elif key in ("maxLength", "maxItems", "maximum"):
            merged[key] = min(merged[key], value)
        elif key in ("minLength", "minItems", "minimum"):
            merged[key] = max(merged[key], value)
        elif key == "type":
            allowed = [t for t in _types(merged[key]) if t in _types(value)]
            if not allowed:
                raise SchemaDerivationError(f"{where}: no common type")
            merged[key] = allowed[0] if len(allowed) == 1 else allowed
        elif merged[key] != value:
            raise SchemaDerivationError(f"{where}: cannot combine {key!r}")
    if "const" in merged and merged["const"] not in merged.pop(
        "enum", [merged["const"]]
    ):
        raise SchemaDerivationError(f"{where}: const is not in enum")
    return merged


def _types(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def _any_of(variants: list[dict]) -> dict:
    return variants[0] if len(variants) == 1 else {"anyOf": variants}


def _check_keys(schema: dict, allowed: frozenset[str], where: str) -> None:
    unknown = set(schema) - allowed
    if unknown:
        raise SchemaDerivationError(f"{where}: unsupported keywords {sorted(unknown)}")


def _check_target_names(target_schema: dict, names: list[str]) -> None:
    validator = Draft202012Validator(target_schema)
    invalid = [name for name in names if not validator.is_valid(name)]
    if invalid:
        raise ValueError(f"not valid target names under the step schema: {invalid}")


def _cap_strings(schema: dict, max_text: int) -> None:
    """Give every free string (no enum or const) a maxLength of at most max_text."""
    is_free_string = "string" in _types(schema.get("type", [])) and not (
        {"enum", "const"} & schema.keys()
    )
    if is_free_string:
        schema["maxLength"] = min(schema.get("maxLength", max_text), max_text)
    for sub in schema.get("properties", {}).values():
        _cap_strings(sub, max_text)
    if "items" in schema:
        _cap_strings(schema["items"], max_text)
    for sub in schema.get("anyOf", []):
        _cap_strings(sub, max_text)


def _check_grammar_friendly(schema: object, where: str) -> None:
    if not isinstance(schema, dict):
        raise SchemaDerivationError(
            f"{where}: boolean subschema left in the generation schema"
        )
    left = NOT_FOR_GRAMMAR & schema.keys()
    if left:
        raise SchemaDerivationError(
            f"{where}: {sorted(left)} left in the generation schema"
        )
    for name, sub in schema.get("properties", {}).items():
        _check_grammar_friendly(sub, f"{where}.{name}")
    if "items" in schema:
        _check_grammar_friendly(schema["items"], f"{where}[]")
    for i, sub in enumerate(schema.get("anyOf", [])):
        _check_grammar_friendly(sub, f"{where}|{i}")


# --- Prompt -------------------------------------------------------------------

SYSTEM_PROMPT = """\
You turn Turkish test instructions for a Windows desktop app into test steps.
Answer with JSON only: {{"version": "{version}", "steps": [...]}}.

Keywords:
- Click: click the target.
- Type: type value into the target; it replaces the text.
- Select: choose the item whose text is value in the target list.
- Verify: check the target with checkpoint {{property, operator, expected}}.
  property: name = text shown by a label, message, button or table;
  value = text inside an input box or combo box;
  enabled, visible, checked, selected = true/false states.
  operator: equals, notEquals or contains. expected: the text, or true/false.
- Wait: wait until the target is ready.
Add timeoutMs (milliseconds) only when the instruction gives a time limit.

target must be one of these objects (Turkish description after the dash):
{objects}

Keep the order of the actions in the instruction. Add no steps it does not ask for."""


def build_messages(text: str, objects: Mapping[str, str], version: str) -> list[dict]:
    """Chat messages for one instruction; `objects` maps logical name -> description."""
    listing = "\n".join(
        f"- {name} — {description}" if description else f"- {name}"
        for name, description in objects.items()
    )
    system = SYSTEM_PROMPT.format(version=version, objects=listing)
    return [{"role": "system", "content": system}, {"role": "user", "content": text}]


# --- Generation ---------------------------------------------------------------


class Status(StrEnum):
    OK = "ok"
    INVALID_JSON = "invalid_json"
    TRUNCATED = "truncated"  # num_predict reached before the JSON was closed
    INVALID_SCHEMA = "invalid_schema"
    UNKNOWN_TARGET = "unknown_target"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"


@dataclass(frozen=True)
class GenerationSettings:
    model: str = "qwen3:8b"
    format: str = "schema"  # "schema": derived schema; "json": any JSON (baseline)
    num_predict: int = 512  # ~25-40 tokens per step; caps a runaway output
    num_ctx: int = 4096
    seed: int = 42
    max_steps: int = 12
    max_text: int = 200


@dataclass
class GenerationResult:
    status: Status
    document: dict | None = None  # the validated step document; None unless ok
    output: str | None = None  # raw model text
    errors: list[str] = field(default_factory=list)
    latency_s: float = 0.0  # wall clock of the request, model load included
    load_s: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    done_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.OK

    def to_dict(self) -> dict:
        return {**asdict(self), "status": str(self.status), "ok": self.ok}


class ChatClient(Protocol):
    def chat(self, body: dict) -> dict: ...


class StepGenerator:
    def __init__(
        self,
        client: ChatClient | None = None,
        settings: GenerationSettings | None = None,
        step_schema: dict | None = None,
    ) -> None:
        self.client = client if client is not None else OllamaClient()
        self.settings = settings or GenerationSettings()
        if self.settings.format not in ("schema", "json"):
            raise ValueError(f"unknown format {self.settings.format!r}")
        self.validator = StepValidator(step_schema)
        self.version = self.validator.schema["properties"]["version"]["const"]

    def request_body(self, text: str, objects: Mapping[str, str]) -> dict:
        s = self.settings
        if s.format == "schema":
            fmt = generation_schema(
                self.validator.schema,
                list(objects),
                max_steps=s.max_steps,
                max_text=s.max_text,
            )
        else:
            fmt = "json"
        return {
            "model": s.model,
            "messages": build_messages(text, objects, self.version),
            "format": fmt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "seed": s.seed,
                "num_ctx": s.num_ctx,
                "num_predict": s.num_predict,
            },
        }

    def warm_up(self) -> None:
        """Load the model so the first timed request does not pay for it."""
        self.client.chat({"model": self.settings.model, "messages": []})

    def generate(
        self, text: str, objects: Mapping[str, str], scenario: str | int | None = None
    ) -> GenerationResult:
        """Steps for one Turkish instruction; `objects` maps logical name -> description.

        Model and server failures come back as a result with `ok == False`. An
        empty `objects` or a name the step schema does not allow is a caller
        error and raises ValueError.
        """
        body = self.request_body(text, objects)
        started = time.perf_counter()
        try:
            reply = self.client.chat(body)
        except ModelTimeout as exc:
            result = GenerationResult(Status.TIMEOUT, errors=[str(exc)])
        except ModelServerError as exc:
            result = GenerationResult(Status.SERVER_ERROR, errors=[str(exc)])
        else:
            result = self._check(reply, objects)
        result.latency_s = round(time.perf_counter() - started, 3)
        _log_result(scenario, self.settings.model, result)
        return result

    def _check(self, reply: dict, objects: Mapping[str, str]) -> GenerationResult:
        result = GenerationResult(
            Status.OK,
            output=(reply.get("message") or {}).get("content") or "",
            load_s=_seconds(reply.get("load_duration")),
            prompt_tokens=reply.get("prompt_eval_count"),
            output_tokens=reply.get("eval_count"),
            done_reason=reply.get("done_reason"),
        )
        try:
            document = json.loads(result.output)
        except json.JSONDecodeError as exc:
            truncated = result.done_reason == "length"
            result.status = Status.TRUNCATED if truncated else Status.INVALID_JSON
            result.errors = [f"invalid JSON: {exc}"]
            return result
        result.errors = self.validator.schema_errors(document)
        if result.errors:
            result.status = Status.INVALID_SCHEMA
            return result
        result.errors = self.validator.unknown_targets(document, objects)
        if result.errors:
            result.status = Status.UNKNOWN_TARGET
            return result
        result.document = document
        return result


def _seconds(nanoseconds: int | None) -> float | None:
    return round(nanoseconds / 1e9, 3) if nanoseconds is not None else None


def _log_result(
    scenario: str | int | None, model: str, result: GenerationResult
) -> None:
    """One JSON line per scenario: the latency record of #37."""
    record = {
        "ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "event": "generate",
        "scenario": scenario,
        "model": model,
        "status": str(result.status),
        "latency_ms": round(result.latency_s * 1000),
        "load_ms": None if result.load_s is None else round(result.load_s * 1000),
        "prompt_tokens": result.prompt_tokens,
        "output_tokens": result.output_tokens,
        "steps": len(result.document["steps"]) if result.document else None,
    }
    log.info(json.dumps(record, ensure_ascii=False))


# --- Batch CLI ----------------------------------------------------------------


def percentile(values: Sequence[float], q: float) -> float | None:
    """q-th percentile, linear between closest ranks (numpy's default)."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def run_batch(
    generator: StepGenerator, cases: Sequence[dict], objects: Mapping[str, str]
) -> list[dict]:
    rows = []
    for case in cases:
        result = generator.generate(case["text"], objects, scenario=case.get("id"))
        row = {"id": case.get("id"), "text": case["text"], **result.to_dict()}
        row["keywords"] = (
            [step["keyword"] for step in result.document["steps"]] if result.ok else []
        )
        if "expected" in case:
            row["expected"] = case["expected"]
            row["keyword_match"] = row["keywords"] == case["expected"]
        rows.append(row)
        print(
            f"#{row['id']} {result.status} {result.latency_s:.2f}s {row['keywords']}",
            flush=True,
        )
    return rows


def summarize(rows: Sequence[dict]) -> dict:
    latencies = [row["latency_s"] for row in rows]
    tokens = [row["output_tokens"] for row in rows if row["output_tokens"] is not None]
    summary = {
        "n": len(rows),
        "ok": sum(row["ok"] for row in rows),
        "ok_rate": round(sum(row["ok"] for row in rows) / len(rows), 3)
        if rows
        else None,
        "by_status": dict(Counter(row["status"] for row in rows)),
        "latency_p50_s": _round(percentile(latencies, 50)),
        "latency_p95_s": _round(percentile(latencies, 95)),
        "latency_max_s": _round(max(latencies, default=None)),
        "output_tokens_median": statistics.median(tokens) if tokens else None,
    }
    if any("expected" in row for row in rows):
        summary["keyword_match"] = sum(row.get("keyword_match", False) for row in rows)
    return summary


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ayna_ai.generate",
        description="Generate step documents for Turkish test instructions with a local model.",
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="JSON lines {id, text, expected?}"
    )
    parser.add_argument(
        "--objects",
        type=Path,
        required=True,
        help="JSON object: logical name -> description",
    )
    parser.add_argument("--model", default=GenerationSettings.model)
    parser.add_argument("--out", type=Path, required=True, help="results JSON")
    parser.add_argument(
        "--log", type=Path, help="per-scenario JSON lines log (default: stderr)"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="loopback Ollama URL")
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="seconds per request"
    )
    parser.add_argument(
        "--num-predict", type=int, default=GenerationSettings.num_predict
    )
    parser.add_argument(
        "--format",
        choices=["schema", "json"],
        default="schema",
        help="schema: derived-schema constraint (default); json: any JSON, as a baseline",
    )
    parser.add_argument(
        "--schema", type=Path, help="step schema (default: schemas/step.schema.json)"
    )
    parser.add_argument(
        "--warmup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="load the model before the timed requests",
    )
    parser.add_argument("--note", default="", help="free text stored in the results")
    args = parser.parse_args(argv)

    try:
        client = OllamaClient(args.host, args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    objects = json.loads(args.objects.read_text(encoding="utf-8"))
    if not isinstance(objects, dict):
        parser.error("--objects must hold a JSON object: logical name -> description")
    cases = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line
    ]
    settings = GenerationSettings(
        model=args.model, format=args.format, num_predict=args.num_predict
    )
    step_schema = load_step_schema(args.schema) if args.schema else None
    generator = StepGenerator(client, settings, step_schema)

    handler = (
        logging.FileHandler(args.log, "w", "utf-8")
        if args.log
        else logging.StreamHandler()
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    started = datetime.now().astimezone()
    try:
        warmup_s = None
        if args.warmup:
            began = time.perf_counter()
            try:
                generator.warm_up()
            except ModelServerError as exc:
                print(f"Warm-up failed: {exc}", file=sys.stderr)
                return 2
            warmup_s = round(time.perf_counter() - began, 2)
        rows = run_batch(generator, cases, objects)
    finally:
        log.removeHandler(handler)
        handler.close()

    try:
        ollama_version = client.version()
    except ModelServerError:
        ollama_version = None
    results = {
        "started": started.isoformat(timespec="seconds"),
        "note": args.note,
        "input": str(args.input),
        "objects": str(args.objects),
        "host": client.host,
        "settings": asdict(settings),
        "warmup_s": warmup_s,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "ollama": ollama_version,
        },
        "summary": summarize(rows),
        "scenarios": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Results: {args.out}")
    print(json.dumps(results["summary"], ensure_ascii=False))
    return 0 if results["summary"]["ok"] == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
