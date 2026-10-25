# Local LLM smoke test: Turkish → JSON steps (#7)

Spike, 2026-10-25, galip. Question: can a 7-8B open-weight model on a team laptop turn Turkish test instructions into schema-valid JSON steps, and how fast and how big is it?

**Answer: yes.** Both models produced schema-valid JSON for at least 9 of 10 sentences (criterion: 8 of 10), and they did so again with Wi-Fi off. They generated about 15–20 tokens/s and needed about 3–5 GB of memory on a 16 GB MacBook. One sentence took about 2–7 s once the model was loaded.

## Setup

| | |
|---|---|
| Machine | MacBook, Apple M2, 16 GB unified memory, macOS 26.6.2, on power |
| Runtime | Ollama 0.40.11 (Homebrew), `ollama serve` with `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=1` |
| Request | `/api/chat`, `format` = [`step-spike.schema.json`](step-spike.schema.json), `think: false`, temperature 0, seed 42, `num_ctx` 4096, no `num_predict` cap |
| Inputs | 10 Turkish sentences, 1–4 steps each, 25 steps in total: [`llm-smoke-inputs.jsonl`](llm-smoke-inputs.jsonl) |
| Grounding | The system prompt lists 17 object names of a fake customer-records app with Turkish descriptions. The schema does **not** restrict `target` to them. |
| Script | [`llm_smoke.py`](llm_smoke.py) (stdlib only, refuses non-loopback hosts) |
| Raw results | [`results/llm-smoke-20261025-1941.json`](results/llm-smoke-20261025-1941.json) (online), [`results/llm-smoke-20261025-1958.json`](results/llm-smoke-20261025-1958.json) (Wi-Fi off) |

| Model tag | Params | Quant | On disk | Licence |
|---|---|---|---|---|
| `qwen3:8b` | 8.2B | Q4_K_M | 5.2 GB | Apache-2.0 |
| `gemma4:e4b-it-qat` | 7.5B (+0.5B vision/audio projector) | Q4_0 (QAT) | 6.1 GB | Apache-2.0 |

The two models are from different families and both are recent. `qwen3.5:9b` (6.6 GB) was left out because of free disk space (18 GB before the downloads).

## Results

From the online run at 19:41. The Wi-Fi-off run is compared under *Offline run*.

| | qwen3:8b | gemma4:e4b-it-qat |
|---|---|---|
| Valid JSON | **10/10** | **9/10** |
| Schema-valid | **10/10** | **9/10** |
| Keyword sequence as expected | 9/10 | 9/10 |
| All targets from the object list | 10/10 | 9/10 |
| Generation, tokens/s (median) | **15.4** | **18.2** (21–22 before the runaway, 16–18 after) |
| Prompt processing, tokens/s (median, ~390 tokens) | 1024 | 206 |
| Time per sentence (median, model loaded) | 3.4 s | 5.8 s |
| First load (cold) | 7.6 s | 10.2 s |
| Memory, Ollama-reported (`/api/ps`) | **4.5 GB** | **2.9 GB** |
| Memory, runner RSS peak | 3.6 GB | 3.9 GB |

Both models meet the acceptance criterion (at least 8 of 10 valid under the schema constraint).

**About the memory numbers.** The machine was already using 6 GB of swap because of other apps. macOS can drop pages of the mmap'd weights under that pressure, so RSS is a lower bound. Ollama's reported size (weights plus KV cache plus buffers) is the better number to plan with. Either way, one model fits in 16 GB with room left for the agent, the client and the server, but not two at once.

## Findings

1. **A schema constraint does not guarantee valid JSON.** For gemma4 #5 (*"Müşteri tablosu görünene kadar en fazla 5 saniye bekle."*), the model opened the `value` string and then repeated `}<tool_call|>` inside it until it hit the context limit: 3712 tokens in 204 s. The grammar allows any character inside a free string, so the output never closed. Fix for #37:
   - give `value` and `target` a `maxLength`;
   - make `target` an `enum` built from the repository objects;
   - cap `num_predict` (for example 256);
   - treat a timeout as a failed generation.
2. **Semantic misses happen even when the JSON is valid.** qwen3 #8 (*"Kaydet'e bastıktan sonra … doğrula ve Tamam'a tıkla"*) dropped the first Click on `customer.saveButton`; the schema cannot catch this. Gemma4 got that sentence right. This is what RQ3 will measure on the real dataset (#35, #56).
3. **Listing the object names in the prompt grounded every target.** No step in a valid response used a target outside the list, even though the schema did not enforce it. That is promising for C1, but 10 sentences against 17 objects is far easier than a real repository.
4. **Turkish suffixes were handled.** Both models turned *Ankara'yı* into `Ankara` and *Yılmaz'ın* into `Yılmaz`. Gemma4 also mapped *Kaydet'e* to `customer.saveButton`. Both kept the Turkish characters in values (`Kayıt başarılı`, `Hatalı şifre`).
5. **Both models think by default.** Pass `think: false`. If thinking is on, the response comes in a separate field, which wastes tokens and time.
6. **Prompt processing speed differs a lot.** qwen3 processes the ~390-token prompt about 5× faster than gemma4. With a large repository in the prompt, this will matter more than generation speed. Retrieval (#57) should keep the prompt short.
7. **Gemma4 slowed down from about 21 to about 17 tokens/s after its 204 s runaway.** This is probably thermal throttling and should be kept in mind when timing long runs on a laptop.

## Offline run

Galip repeated the run on 2026-10-25 at 19:58 with Wi-Fi off. `ping 1.1.1.1` failed with "No route to host". The Ollama server and the settings were the same as in the online run.

| | qwen3:8b | gemma4:e4b-it-qat |
|---|---|---|
| Schema-valid | **10/10** | **9/10** |
| Keyword sequence as expected | 9/10 | 9/10 |
| Generation, tokens/s (median) | 16.2 | 18.8 |
| Time per sentence (median) | 3.3 s | 5.3 s |
| First load | 5.9 s | 7.6 s |
| Memory, Ollama-reported / RSS peak | 4.9 / 5.0 GB | 2.9 / 4.0 GB |

The steps were the same as in the online run: the same miss (qwen3 #8) and the same runaway (gemma4 #5, 3712 tokens again). With temperature 0 and a fixed seed the outputs are reproducible, which is useful for evaluation. Memory varied between the runs (qwen3: 4.5 vs 4.9 GB reported), so plan with about 5 GB per 8B model.

## Next

- #37 (constrained generation): apply finding 1 and compare runs with and without the schema.
- #71 (model comparison): add `qwen3.5:9b` and a larger model once more disk space or the department GPU is available. The access request is drafted in [`gpu-request-draft.md`](gpu-request-draft.md).
- The real `schemas/step.schema.json` does not exist yet. This spike's schema is throwaway.
