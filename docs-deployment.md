# Deployment notes

Every claim below was read from the provider's own documentation on
2026-11-15 (rendered pages), unless marked UNVERIFIED. Tiers change;
re-check before relying on them.

## Model options for behavior.json (backend: openai-compatible)

### Groq free plan (VENDOR: console.groq.com/docs/rate-limits)
- Free plan models and limits (per model): openai/gpt-oss-120b,
  openai/gpt-oss-20b, qwen3.8-27b - each 30 RPM, 1K RPD, 8K TPM,
  200K TPD. Groq notes the table is a high-level summary; exact limits
  show in the account's limits page. Note these are REQUEST limits: an
  assistant that makes several model calls per user message consumes
  several requests per message.
- OpenAI-compatible endpoint (VENDOR: console.groq.com/docs/openai):
  base_url https://api.groq.com/openai/v1 - Denyut's backend speaks this.
- UNVERIFIED: whether signup needs a card; the "inputs not used for
  training" claim (their Services Agreement page did not render; a
  third-party roundup quotes it - treat as a lead only).

### OpenRouter free models (VENDOR: openrouter.ai/docs/api-reference/limits)
- Models with a ":free" suffix: 20 requests/min; 50 requests/day if
  lifetime credits purchased < 10; 1000/day once >= 10 credits purchased
  (one-time). Negative balance blocks free models too.
- Free models can 429 when the upstream provider is saturated.

### Google Gemini API free tier (VENDOR: ai.google.dev/gemini-api/docs)
- Free tier exists for select models (Flash family); exact per-model
  limits are shown in AI Studio.
- PRIVACY: the vendor pricing page marks the free tier as "Content used
  to improve our products" (paid tiers: not used).

### On-device (no account, most private)
- No on-device measurement exists yet (mid-range Helio G99-class hardware or comparable).
  Speed and quality on a real phone are UNKNOWN until measured.

## Bot host options

### Oracle Cloud Always Free (VENDOR: docs.oracle.com Free Tier pages)
- Always Free offers never expire.
- Compute: VM.Standard.A1.Flex (Arm) - first 1,500 OCPU-hours and 9,000
  GB-hours per month free, equivalent to 2 OCPUs + 12 GB RAM always on;
  plus up to two VM.Standard.E2.1.Micro (AMD) instances. Home region
  only; region capacity for free shapes varies.
- Idle Always Free compute instances may be reclaimed. Oracle's idle
  criteria are 7-day utilization thresholds (CPU, network, memory), not
  whether a process is running; a low-traffic bot VM could still look
  idle. Treat reclamation risk as real; costs are conditional, not
  guaranteed $0.
- Signup: "most users need a mobile phone number and a credit card";
  card not charged unless the account is upgraded.

### Android app on the owner's phone (OFFICIAL ARTIFACTS EXIST)
- chatmail/core v2.69.0 releases officially ship:
  - deltachat-rpc-server-arm64-v8a-android (and armeabi-v7a) binaries
  - deltachat_rpc_server-2.69.0-py3-none-android_21_arm64_v8a.whl
    (Python wheel tagged for Android, binary bundled in-package)
- Chaquopy (VENDOR: chaquo.com docs) embeds Python on Android and
  supports arm64-v8a; current Chaquopy supports
  Python >= 3.12, which satisfies deltachat2's Python >= 3.11 need.
- So: Kotlin app shell + Chaquopy + deltabot-cli/deltachat-rpc-client +
  the official Android wheel = the same Denyut Python core running inside
  an Android app on the owner's phone. Feasibility is artifact-grounded; the integration
  itself is unbuilt and untested, and Android background/battery limits
  apply. APK builds can run in GitHub Actions.
