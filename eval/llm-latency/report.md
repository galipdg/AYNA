# NFR-12 — local-model latency on Windows

Measured 2026-11-14 by hasan on the team's only Windows machine, for #162. Every number below
is re-derivable from `results/*.json`; the harness is `run.py` and it drives `ayna_ai`, not a
copy of it.

## The short answer

1. **This machine is not the machine the requirement is about.** It has an RTX 3060 Laptop
   (6 GB) and Ollama offloads to it, so its default numbers are *better* than the Mac's, not
   worse. Forced CPU-only — the closed-network box NFR-12 actually targets — it is **2.7×
   slower than the Mac** on the same path.
2. **30 s is not a safe deadline for a CPU-only Windows box.** With `reasons` on, as the
   service ships, **p95 is 41–43 s and 20–30 % of requests exceed 30 s**. Recommended
   deployment default: **60 s**, with 30 s defensible only where the model sits wholly in VRAM.
3. **`reasons` should become opt-in per request.** It is the cheapest lever by a wide margin:
   CPU-only p95 goes 22.68 s → 43.10 s and the share over 30 s goes 0/10 → 2/10, with the
   prompt and schema otherwise identical.
4. **The model ranking is the opposite of the Mac's, and the cause is VRAM, not quality.**
   `gemma4:e4b-it-qat` loads as 3.1 GB and runs **100 % on the GPU**; `qwen3:8b` loads as
   6.0 GB, does not fit, and runs **30 % CPU / 70 % GPU**. So gemma4 is **3.2× faster here**
   while being *slower* on the Mac — and it matched the expected keyword sequence 10/10 against
   qwen3's 9/10. Default to gemma4 on any box with under 8 GB of VRAM.

## The machine

| | |
|---|---|
| CPU | AMD Ryzen 7 6800H, 8 cores / 16 threads, 3.2 GHz max |
| RAM | 15.3 GB usable |
| GPU | NVIDIA GeForce RTX 3060 Laptop, **6144 MiB**, driver 566.07, compute 8.6 |
| OS | Windows 11 Pro 10.0.26300 |
| Runtime | Ollama 0.40.16, `127.0.0.1:11434`, `num_ctx` 4096, temperature 0, seed 42 |
| Loaded size / offload | `qwen3:8b` 6.0 GB → 30 % CPU / 70 % GPU · `gemma4:e4b-it-qat` 3.1 GB → **100 % GPU** |
| Inputs | the same 10 Turkish sentences as the Mac runs (`ai/spikes/llm-smoke-inputs.jsonl`) |

**Ollama was already installed when this work started** and both models were already pulled,
so the issue's first step was done before it began. Both facts contradict the issue body and
are left there rather than edited, because the second one changes what the result means.

## Group A — as Ollama chooses (what this laptop does), idle

| run | path | model | p50 s | p95 s | max s | ok | over 30 s |
|---|---|---|---|---|---|---|---|
| `cli-qwen-gpu` | cli | qwen3:8b | 5.34 | 8.38 | 9.18 | 10/10 | 0/10 |
| `cli-gemma-gpu` | cli | gemma4 | **1.65** | **2.47** | 2.66 | 10/10 | 0/10 |
| `cli-qwen-gpu-json` | cli | qwen3:8b | 4.73 | 7.82 | 8.81 | **0/10** | 0/10 |
| `cli-qwen-gpu-reasons` | cli | qwen3:8b | 8.48 | 14.23 | 15.54 | 10/10 | 0/10 |
| `http-qwen-gpu` | http | qwen3:8b | 8.59 | 16.04 | 18.65 | 10/10 | 0/10 |
| `http-gemma-gpu` | http | gemma4 | **2.36** | **3.56** | 3.97 | 10/10 | 0/10 |

## Group B — forced CPU-only (the closed-network box), idle

| run | path | model | p50 s | p95 s | max s | ok | over 30 s |
|---|---|---|---|---|---|---|---|
| `cli-qwen-cpu` | cli | qwen3:8b | 15.30 | 22.68 | 25.00 | 10/10 | 0/10 |
| `cli-gemma-cpu` | cli | gemma4 | 14.29 | 19.64 | 20.63 | 10/10 | 0/10 |
| `cli-qwen-cpu-reasons` | cli | qwen3:8b | 23.31 | **43.10** | 49.43 | 10/10 | **2/10** |
| `http-qwen-cpu` | http | qwen3:8b | 23.24 | **41.30** | 47.97 | 10/10 | **2/10** |

## Under load — 8 CPU-bound processes of 16 threads (56–60 % busy)

| run | path | model | p50 s | p95 s | max s | over 30 s | idle p50 |
|---|---|---|---|---|---|---|---|
| `cli-gemma-gpu+load8` | cli | gemma4 | 1.70 | 2.48 | 2.77 | 0/10 | 1.65 |
| `cli-qwen-gpu+load8` | cli | qwen3:8b | 6.29 | 10.09 | 10.97 | 0/10 | 5.34 |
| `http-qwen-cpu+load8` | http | qwen3:8b | 22.75 | **43.33** | 48.46 | **3/10** | 23.24 |

**A model that sits wholly in VRAM is almost immune to the machine's own load**: gemma4 moved
1.65 → 1.70 s, while qwen3, 30 % of which is on the CPU, moved 5.34 → 6.29 s (+18 %). This
matters more than it looks, because AYNA's agent, client and server all run on the same box
while a test is playing.

The CPU-only service was barely affected at the median (23.24 → 22.75 s) but its **tail grew
and the deadline share went 2/10 → 3/10**. Under load the damage is in the tail, which is
exactly where a 30 s deadline lives.

## Next to the Mac

| Measurement | Mac M2 (#37/#71) | Windows, GPU | Windows, CPU only |
|---|---|---|---|
| `ayna_ai.generate`, qwen3:8b, schema | 5.61 / 9.07 | **5.34 / 8.38** | 15.30 / 22.68 |
| `ayna_ai.generate`, gemma4 | 6.22 / 8.68 | **1.65 / 2.47** | 14.29 / 19.64 |
| `POST /ai/generate-steps`, reasons on | 12.60 / 25.30 | **8.59 / 16.04** | 23.24 / 41.30 |
| `POST /ai/generate-steps`, reasons off | 8.80 / 21.40 | not runnable (see below) | not runnable |

p50 / p95 in seconds. **The Mac's 504 at 30.0 s did not recur on this machine in any
configuration** — but that is the GPU doing it: CPU-only, two or three requests in ten pass
30 s in every configuration that has `reasons` on.

## Recommendations

**A Windows deployment default of 60 s**, not 30 s. The worst realistic case measured here is
p95 43.33 s (CPU-only, reasons on, 60 % busy) with a worst single request of 48.46 s; 60 s
leaves roughly 1.4× headroom over that p95. Keep 30 s only where the model is known to sit
wholly in VRAM — there the worst p95 measured is 16.04 s. A deadline is not a latency target,
so raising it does not weaken NFR-12; what it changes is whether the panel shows a failure or
an answer.

**Make `reasons` opt-in per request (#78), default off.** On the CPU-only box it is the
difference between a p95 under the deadline and 20 % of requests failing, for ~55 % more output
tokens (median 103 against 66.5). The panel can ask for reasons on a second, explicit request
when a user wants them.

**Default to `gemma4:e4b-it-qat` where VRAM is under 8 GB.** On this machine it is 3.2× faster
than `qwen3:8b` and matched the expected keyword sequence 10/10 against 9/10 — faster *and* at
least as good here. The reason is that it fits in 6 GB and qwen3:8b does not, so the
recommendation is about the box, not the model: with 12 GB or more of VRAM the comparison
needs redoing.

**Warm every offered model at start, not just the default.** The service warms its default
model only, so the first request against any other one pays the whole load: 14.71 s on the GPU
and **25–51 s CPU-only**. An early measurement of mine was spoiled by exactly this.

## What this does not establish

- **Ten sentences, one run each.** A p95 over 10 samples is an interpolation between the 9th
  and 10th value, so treat every p95 here as indicative and the p50s as the solid numbers.
- **Output is not reproducible run to run, even at temperature 0 with seed 42.** Comparing the
  two CPU-only service runs — same model, prompt, schema, seed, with only the machine load
  differing — **1 of the 10 sentences produced a different keyword sequence** (`#1`:
  `Type, Type, Click` idle against `Click, Type, Click, Type, Click` under load). This
  contradicts `ai/spikes/llm-smoke.md`'s "with temperature 0 and a fixed seed the outputs are
  reproducible, which is useful for evaluation" and matters for **RQ3 (#77)**, which compares
  accuracy across runs. One observation, not a study; worth its own issue.
- **The unconstrained `json` baseline scored 0/10**, and not for lack of understanding: the
  model wrote `action` where the schema wants `keyword`, with the targets and values correct
  (`login.userNameInput`, `Type`, `admin`). So the derived schema is load-bearing for validity
  and costs about 0.6 s of p50 — a bargain, and a stronger result than PR #142's.
- **HTTP without `reasons` could not be measured**, because the service hard-codes
  `reasons=True` (`ai/ayna_ai/service.py:181`) and its request schema has no such field. The
  cost of `reasons` is therefore measured on the CLI path, where it is one flag on the same
  code — which is a cleaner isolation anyway. A toggle is requested from galip.
- **One machine, one GPU, one driver.** This replaces an Apple-silicon-only picture with a
  two-point one; it is not a hardware survey. The D2/#131 GPU argument is now supported by a
  measured 2.7× CPU-only penalty rather than an assumption.

## Two measurement errors this harness caught in itself

Both are in the git history and both would have been published as findings:

- `StepGenerator.warm_up` does not go through `request_body`, so the CPU-only runs warmed up
  whichever offload was already loaded and the **first timed request paid for the reload**: a
  run printed `warm-up 0.0s` beside a 34.48 s first request against a 15.3 s median, and
  reported a false `1/10 over 30 s`. `CpuOnly.warm_up` now asks for `num_gpu` 0 and the rerun
  gave 0/10.
- The HTTP path did not warm the requested model, so `http-gemma-gpu` first came out at p95
  9.87 s with a p50 of 2.43 s — a cold load inside the sample. Warmed, it is p95 3.56 s.

`check_offload` now reads `size_vram` from `/api/ps` before every run and refuses to record one
whose offload is not what the configuration claims. That guard is what makes the CPU-only
numbers trustworthy, and it is also what revealed that **Ollama reuses a runner already loaded
CPU-only** instead of reloading it for a request that does not mention the offload — which is
the only reason a CPU-only measurement of the HTTP path is possible at all.
