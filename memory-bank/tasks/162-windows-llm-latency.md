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
- [x] `eval/llm-latency/run.py`, the matrix, 24 tests, README — `6b18e05` and after
- [x] **All 13 runs done, 2026-11-14, machine idle (and three under load)** — group A (GPU),
      group B (forced CPU-only), group C (8 busy processes of 16 threads)
- [x] **`eval/llm-latency/report.md`** — the tables, the Mac comparison, the recommended
      Windows default, the `reasons` recommendation and what the result does not establish
- [ ] Criterion 5 (`ai/README.md`, `ai/API.md` label which latencies are Apple-silicon): galip's
      files, requested in his inbox with the numbers
- [ ] Post the numbers on #162 and open the PR
- Next step: post the report's "short answer" as a comment on #162, then open the PR.

## The answers, in one place

- **30 s is not safe for a CPU-only Windows box**: with `reasons` on, as the service ships,
  p95 is 41–43 s and **2–3 of every 10 requests exceed 30 s**. Recommended deployment default
  **60 s** (~1.4× the worst measured p95 of 43.33 s); 30 s only where the model sits wholly in
  VRAM, where the worst p95 is 16.04 s.
- **`reasons` should be opt-in per request (#78), default off** — on the CPU-only box it is the
  difference between p95 22.68 s (0/10 over the deadline) and p95 43.10 s (2/10), for ~55 % more
  output tokens. Same prompt, same schema, one flag.
- **Default to `gemma4:e4b-it-qat` under 8 GB of VRAM**: 3.2× faster than `qwen3:8b` here and
  10/10 keyword matches against 9/10. The cause is fit, not quality — gemma4 loads as 3.1 GB and
  runs **100 % GPU**, qwen3:8b loads as 6.0 GB and runs **30 % CPU / 70 % GPU** in 6 GB of VRAM.
  **This is the reverse of the Mac's ranking**, where gemma4 was the slower of the two.
- **A fully VRAM-resident model is almost immune to the machine's own load** (gemma4 1.65 →
  1.70 s under 59 % busy; qwen3 5.34 → 6.29 s). Relevant because the agent, client and server
  share the box during a run.
- **Warm every offered model at start, not just the default** — the first request against a
  non-default model pays 14.71 s on the GPU and 25–51 s CPU-only.

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
- `ai/spikes/` is excluded from ruff and has no CI job, and `eval/llm-latency/` is the second
  eval folder to need adding to `eval/pyproject.toml`'s `testpaths` by hand (#29 hit this too).
  Worth one issue about `testpaths` rather than a third manual edit. **It also means #29 and
  #162 both edit that one line and will conflict on merge** — whichever lands second keeps both
  entries (`rq1/tests` and `llm-latency/tests`).
- **Output is not reproducible run to run, even at temperature 0 with seed 42.** The two
  CPU-only service runs differ on 1 of 10 sentences with only the machine load changed (`#1`:
  `Type, Type, Click` idle, `Click, Type, Click, Type, Click` under load). This contradicts
  `ai/spikes/llm-smoke.md`'s reproducibility claim and matters for **RQ3 (#77)**, which compares
  accuracy across runs. One observation, not a study — worth its own issue, and galip's call
  since #77 and the spike are his.
- **The unconstrained `json` baseline scores 0/10 valid**, and not for lack of understanding:
  the model writes `action` where the schema wants `keyword`, with the targets and values
  correct. So the derived schema is load-bearing for validity and costs ~0.6 s of p50. Stronger
  than PR #142's result and worth saying in `ai/`'s own docs.

## Manual checks

- **DONE** · 2026-11-14 · hasan, on this machine · the full matrix, machine idle for groups A
  and B and under a defined load for group C · evidence: `eval/llm-latency/results/*.json`
  (13 files, each carrying the machine, the offload in VRAM and every row) and
  `eval/llm-latency/report.md`. `busy_before` was 5–11 % for every idle run and 56–60 % for the
  three load runs. The AI service ran with `--timeout 600` so the tail could be measured at all.

## Handoff

The latency numbers are only comparable with the Mac's while the prompt and the derived schema
are unchanged: `PROMPT_VERSION` is `3` and the results files record it per run. A prompt change
in `ai/` voids the comparison, not just the absolute numbers.

## Two measurement errors the harness caught in itself

Both would have been published as findings, and both are now pinned by a test:

- `StepGenerator.warm_up` does not go through `request_body`, so the CPU-only runs warmed
  whichever offload was already loaded and the **first timed request paid for the reload**: one
  run printed `warm-up 0.0s` beside a 34.48 s first request against a 15.3 s median, and
  reported a false `1/10 over 30 s`. `CpuOnly.warm_up` now asks for `num_gpu` 0; the rerun gave
  0/10 and an unchanged p50, which is what confirmed the diagnosis.
- The HTTP path did not warm the *requested* model, only the service's default, so
  `http-gemma-gpu` first came out at p95 9.87 s with a p50 of 2.43 s — a cold load inside the
  sample. Warmed, p95 3.56 s.

`check_offload` reads `size_vram` from `/api/ps` before every run and refuses to record one
whose offload is not what the configuration claims. Writing it revealed the fact the whole
CPU-only HTTP measurement depends on: **Ollama reuses a runner already loaded CPU-only** rather
than reloading it for a request that does not mention the offload. Without that, the service —
which builds its own request and has no `num_gpu` — could not be measured CPU-only at all.

## Outcome (fill when the issue closes)
