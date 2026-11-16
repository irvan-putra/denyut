# Small local model and low-cost provider options for a phone assistant

Status: exploration. Facts re-checked 2026-11-16 where a URL is given. No speed or memory measurements were made on any phone; do not claim any until a test measures them.

## Local model candidate (checked)
- Qwen/Qwen3-1.7B-GGUF, official repository: public (not gated), license apache-2.0, and the repository lists a single GGUF file, Qwen3-1.7B-Q8_0.gguf (about 1.8 GB). https://huggingface.co/api/models/Qwen/Qwen3-1.7B-GGUF
- A smaller quantization from another publisher may fit better on a mid-range phone. That needs a test, not an assumption.
- The 2026-11-12 reading also looked at a Google 1B QAT model. It was gated with non-OSI terms at that time; not re-checked.

## Engine route
llama.cpp ships an HTTP server with an OpenAI-compatible API, so an assistant that already speaks that API can point to localhost. https://github.com/ggml-org/llama.cpp/tree/master/tools/server Running it inside an Android app is a design option that was not tested here. LiteRT-LM was noted as a later alternative (not re-checked).

## Provider cost controls (checked)
- Groq: moving from the free tier to a paid tier needs a payment method (https://console.groq.com/docs/billing-faqs). Spend limits exist only on paid plans, and spend tracking lags by 10-15 minutes, so a small overage is possible (https://console.groq.com/docs/spend-limits).
- OpenRouter: prepaid credits and purchase fee details were read on 2026-11-12 and not re-checked; treat as unverified.
- A hard spending cap is best enforced by the provider side, not by an app's own estimate.

## Design idea (author's proposal)
A setting with three modes (none, local, remote) and a visible fallback from local to remote only through routes that are verified free or hard-capped, with the active backend always shown. The remote mode is opt-in and off by default: prompts are never sent to a remote provider until the user explicitly turns it on, and a local failure must not silently send the prompt remotely; it shows an error and offers the choice.


## Tests still needed
Load time, tokens per second and resident memory of the model on a mid-range phone; behavior when memory is low; whether the engine can run inside an app.
