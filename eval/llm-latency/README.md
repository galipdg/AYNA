# NFR-12 — local-model latency on Windows

**The question (#162):** every latency the project has for the AI service comes from one
MacBook M2, and AYNA ships to a closed **Windows** network. NFR-12 promises a p95 on team
hardware; that number must not be an Apple-silicon one.

```powershell
# from the repository root; no install and no venv of its own -- `ayna_ai` needs only
# `jsonschema`, which `eval` already depends on
.venv/Scripts/python.exe eval/llm-latency/run.py list
.venv/Scripts/python.exe eval/llm-latency/run.py run cli-qwen-gpu
.venv/Scripts/python.exe eval/llm-latency/run.py report

# the HTTP rows need the service up, in another terminal, from `ai/`:
#   python -m ayna_ai.service --models qwen3:8b,gemma4:e4b-it-qat --timeout 600
# measure with the deadline raised, not at its shipped 30 s -- see below

.venv/Scripts/python.exe -m pytest eval/llm-latency/tests
```

Run **one configuration at a time with the machine idle**, and finish a whole group before
starting the next: Ollama reloads the model whenever `num_gpu` changes, so an interleaved
matrix charges half the runs a cold load.

## What is here

| Path | What it is |
|---|---|
| `run.py` | The matrix driver. Imports `ayna_ai.generate` and drives the running service; measures nothing itself. |
| `results/<id>-<stamp>.json` | One run: the config, the machine, the summary, the 30 s share and every row. Never overwritten. |
| `report.md` | The written answer: the tables, the recommended Windows timeout, the `reasons` recommendation. |

## Two things that decide how the numbers read

**This machine has a GPU, and the requirement is about a box that may not.** Ollama offloads
about 70 % of `qwen3:8b` to an RTX 3060 Laptop here (`ollama ps` prints `30%/70% CPU/GPU`), so
the default number is **not** the closed-network box's number. Every configuration therefore
exists twice — group `A-gpu` as Ollama chooses, group `B-cpu` forced CPU-only — and the pair is
what gets reported. `CpuOnly` adds `options.num_gpu = 0` to the request and changes nothing
else: the prompt, the derived schema, the seed and the token caps stay byte-identical, which a
test pins, because otherwise the ratio between the two groups would mean nothing.

**The runs raise the timeout and the 30 s deadline is applied afterwards.** The service answers
504 at `ServiceConfig.timeout_s` = 30 s, so measuring as shipped would censor exactly the tail
the issue asks about. `deadline_share` counts how many requests *would* have become a 504 from
the recorded latencies.

## What `reasons` costs is measured on the CLI path

`service.py` hard-codes `reasons=True` and its request schema has no `reasons` field, so
"HTTP without reasons" cannot be run without changing `ai/`. The CLI takes `reasons` as a
setting, so `cli-qwen-gpu` against `cli-qwen-gpu-reasons` is the same code with one flag
flipped — a cleaner answer to "should `reasons` be opt-in per request?" than the HTTP pair
would have been. A toggle is requested in galip's inbox.

## Comparability

A number here is comparable with the Mac's only while the prompt and the derived schema are
unchanged. `PROMPT_VERSION` is recorded in every results file; a prompt change in `ai/` voids
the comparison, not just the absolute values. The inputs are the same ten Turkish sentences
(`ai/spikes/llm-smoke-inputs.jsonl`) and a test pins that too.
