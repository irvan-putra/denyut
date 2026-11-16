# Gemma and AI Studio: hosted access supplement

Research checked 2026-11-16. Public-source research only. No weights downloaded,
account inspected/created, secret requested, billing enabled, terms accepted,
API request made or implementation selected. This supplements the earlier
local-model research, rather than rewriting its historical observations.

## Bottom line
No supported subscription-only programmatic route was established. A Google
AI app subscription, AI Studio browser interactions, the free Developer API
and billed API usage with promotional credits are different access paths.
For a private/offline Android assistant with no usage-based charges, retain
phone-local Gemma as the first feasibility candidate. A synthetic hosted
experiment is not evidence that a personal production assistant is permitted
or private.

## Current subscription credits, with limits
Google's current AI Studio guide and Nov13 Google announcement say AI Pro
includes $10/month promotional Google Cloud credits, Ultra5x $40/month and
Ultra20x $100/month. Plus does not include this benefit. Each monthly grant
lasts 12 months and is restricted to the primary subscriber. An eligible
account, developer profile, project/API key and billing setup are needed.
The current redemption flow calls for $5 prepayment. After promotional credits
are exhausted, prepaid funds can be used. This is not a flat-fee unlimited API
entitlement. An account's actual entitlement was not inspected.

The short credits guide says project caps can stop paid requests. The more
detailed billing documentation adds a material caveat: project caps are
experimental and have around 10 minutes of billing-processing latency;
overages can occur, including beyond prepaid balance. Do not describe either
as a hard spending ceiling. This route does not meet a strict existing-
subscription-only/no-new-usage-charges boundary without a different verified
arrangement. No activation or prepayment proposed here.

## Free hosted Gemma is separate
Official Gemma API docs list gemma-4-31b-it and gemma-4-26b-a4b-it. Current
pricing lists Gemma4 input/output free tier and paid tier unavailable. A
project and API key are still required. Free tier is not the subscription
benefit and must not silently become a paid fallback. Indonesia is currently
on the supported-region list. Project-specific quotas and verification may
apply; rate limits/capacity are not guaranteed and were not account-checked.

The current API terms say:

> Use of Google AI Studio and Gemini API is for developers building with
> Google AI models for professional or business purposes, not for consumer use.

This does not establish whether a particular developer prototype qualifies;
it means a personal consumer assistant deployment must not be called cleared
without resolving this scope. Current unpaid-services terms also say:

> Do not submit sensitive, confidential, or personal information to the
> Unpaid Services.

They say human reviewers may read, annotate and process inputs/outputs, and
content can be used to improve Google products. Therefore private assistant
notes, messages or credentials are not suitable for an unpaid experiment.
An isolated synthetic developer test is a different proposition from a real
assistant deployment. No browser-chat automation workaround is recommended.

## Integration and local alternative
Gemini API documents OpenAI-compatible chat/completions with an API key, which
resembles Denyut's existing Python backend; exact Gemma/endpoint compatibility
still needs a test. LiteRT-LM Android instead has a Kotlin Engine/Conversation
API and needs an Android/Python bridge. Neither is an already-working Denyut
model integration.

Gemma 4 differs from older Gemma3/3n licensing: current official guidance links
Gemma4 to Apache-2.0. The generic mobile Gemma4 E2B instruction-tuned artifact
is public, ungated and 2,588,147,712 bytes (about 2.59 GB), per unauthenticated
metadata checked on this date. No model weights were retrieved. Google's
mobile text-only static memory estimates are not total app RAM promises or
download sizes. Target-device performance/RAM/storage fit is unmeasured. A pinned
LiteRT-LM Android CPU-first text-only short-context trial is the recommendation
if local execution is chosen; no download or implementation is authorized by
this research. Keep deterministic notes/reminders independent of model choice.

## Sources
Subscription benefit and simplified cap explanation:
- https://aistudio.google.com/learn/claim-google-ai-plan-credits-in-ai-studio
Google announcement, 2026-11-13:
- https://blog.google/innovation-and-ai/technology/developers-tools/google-cloud-credits-gdp-ai-studio/
Detailed billing caveats (also resolves to AI Studio docs):
- https://ai.google.dev/gemini-api/docs/billing
Current pricing:
- https://ai.google.dev/gemini-api/docs/pricing
API terms, including developer-purpose and unpaid-data restrictions:
- https://aistudio.google.com/docs/terms
Supported regions:
- https://aistudio.google.com/docs/available-regions
Quota/verification/capacity caveats:
- https://aistudio.google.com/docs/rate-limits
Hosted Gemma models:
- https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
OpenAI compatibility:
- https://ai.google.dev/gemini-api/docs/openai
Gemma4 variants/memory limits and license:
- https://ai.google.dev/gemma/docs/core
- https://ai.google.dev/gemma/apache_2
LiteRT-LM Android:
- https://github.com/google-ai-edge/LiteRT-LM/blob/main/docs/api/kotlin/getting_started.md
Generic mobile artifact card and metadata:
- https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm
- https://huggingface.co/api/models/litert-community/gemma-4-E2B-it-litert-lm?blobs=true
