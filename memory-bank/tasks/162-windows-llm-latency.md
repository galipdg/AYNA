# #162 Measure local-model latency on Windows

- Issue: https://github.com/galipdg/AYNA/issues/162
- Owner: hasan · Branch: `hasan/162-windows-llm-latency`
- Started: 2026-11-14 · Last update: 2026-11-14

## Approach

Drive **galip's harness, not a copy of it**: `eval/llm-latency/run.py` puts `ai/` on
`sys.path` and imports `ayna_ai.generate` (`StepGenerator`, `run_batch`, `summarize`,
`percentile`) and `ayna_ai.service`. Same pattern and same reason as `eval/rq1/measure.py`
with `ayna_agent`: a second copy of the prompt, the derived schema or the timing would make
this measure the harness instead of the service. `ayna_ai` needs only `jsonschema~=4.26`,
which `eval` already depends on, so **no new dependency and no venv of its own** — the
repository-root `.venv` runs it.

Output lives under `eval/llm-latency/` because `ai/` is galip's area and the issue leaves the
location to him; a request to move it next to the Mac numbers in `ai/spikes/results/` is in
his inbox.

## Decisions (small, local to this task)

- 2026-11-14 — **Measure CPU-only as well as the default GPU offload, and report the pair** —
  the issue's premise is "a Windows test box without a usable GPU", and this machine
  **has** one (RTX 3060 Laptop, 6 GB). Ollama offloads **70 % of `qwen3:8b` to it**
  (`ollama ps`: `30%/70% CPU/GPU`), so the default number here is *not* the closed-network
  box's number and must not be published as it. CPU-only is forced per request with
  `options.num_gpu = 0` through a `StepGenerator` subclass that overrides `request_body`,
  which leaves the prompt, the derived schema and the seed identical — the offload is the
  only thing that changes. `OLLAMA_NUM_GPU` would have needed the server restarted.
- 2026-11-14 — **Group the runs by offload, never interleave them** — Ollama reloads the
  model whenever `num_gpu` changes, so an interleaved matrix would charge every second run a
  cold load and the loads are themselves slower CPU-only.
- 2026-11-14 — **Measure with the deadline raised, and compute the 30 s share afterwards** —
  the service answers 504 at 30 s (`ServiceConfig.timeout_s`), so measuring as shipped would
  censor exactly the tail the issue asks for. Runs use a long `--timeout` and the share of
  requests that *would* have exceeded 30 s is counted from the recorded latencies.
- 2026-11-14 — **The `reasons` cost is isolated on the CLI path, not the HTTP one** — the
  service hard-codes `reasons=True` (`service.py:181`) and its request schema has no
  `reasons` field, so "HTTP without reasons" cannot be run without changing galip's file.
  The CLI takes `reasons` as a setting, so the same code path with one flag flipped answers
  criterion 4 more cleanly than the HTTP pair would. A toggle is requested in galip's inbox.

## Status

- [x] Branch, task note
- [x] Hardware and runtime recorded (below)
- [x] Calibration: `qwen3:8b`, schema, GPU, one sentence — **6.24 s** warm, 3 steps, keyword
      sequence as expected (`load_ms` 16, 467 prompt / 70 output tokens)
- [ ] `eval/llm-latency/run.py` and the run matrix
- [ ] The runs themselves (machine idle)
- [ ] The report: p50/p95 per path and configuration, the 30 s share, a recommended Windows
      default, the `reasons` recommendation
- Next step: write `run.py`, then run group A (GPU) with the machine idle.

## The machine, so no number is read without it

| | |
|---|---|
| CPU | AMD Ryzen 7 6800H, 8 cores / 16 threads, 3.2 GHz max |
| RAM | 15.3 GB usable |
| GPU | **NVIDIA GeForce RTX 3060 Laptop, 6144 MiB**, driver 566.07, compute 8.6 (plus Radeon iGPU) |
| OS | Windows 11 Pro 10.0.26300 |
| Runtime | Ollama **0.40.16**, `127.0.0.1:11434`, models in `%USERPROFILE%\.ollama\models` (11 GB) |
| Models | `qwen3:8b` (5.2 GB), `gemma4:e4b-it-qat` (6.1 GB) — the two measured on the Mac |
| Offload | `qwen3:8b` loads as 6.0 GB, **30 % CPU / 70 % GPU**, 4473 MiB of VRAM in use, `num_ctx` 4096 |

**The issue's body is out of date on two counts**: Ollama was already installed when this
work started, and this machine is not CPU-only. Both are recorded here rather than silently
fixed, because the second one changes what the measurement means.

## Open issues

- **The service cannot be asked for a generation without reasons** (`service.py:181` hard-codes
  `reasons=True`; the request schema has no such field). That is the configuration #78 may want
  and criterion 4 is a recommendation about it, so the toggle is worth having whatever this
  measurement concludes. Requested in galip's inbox; not my file.
- **Criterion 5 is galip's files** (`ai/README.md`, `ai/API.md` must say which published
  latencies are Apple-silicon and which are Windows). Requested in his inbox with the numbers
  once they exist; it cannot be ticked by me.
- `ai/spikes/` is excluded from ruff and has no CI job, and `eval/llm-latency/` would be the
  second eval folder to need adding to `eval/pyproject.toml`'s `testpaths` by hand (#29 hit
  this too). Worth one issue about `testpaths` rather than a third manual edit.

## Manual checks

- (pending) · hasan, on this machine · the full matrix with the machine **idle** — the user
  asked for nothing else running during it.

## Handoff

The latency numbers are only comparable with the Mac's while the prompt and the derived schema
are unchanged: `PROMPT_VERSION` is `3` and the results files record it per run. A prompt change
in `ai/` voids the comparison, not just the absolute numbers.

## Outcome (fill when the issue closes)
