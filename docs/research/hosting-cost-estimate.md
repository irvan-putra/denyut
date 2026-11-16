# Denyut hosting cost estimate (single user)

Checked 16 Nov 2026. Exchange rate: 1 EUR = Rp 20,163.71, dated 13 Nov 2026 ([frankfurter.dev](https://api.frankfurter.dev/v1/latest?base=EUR&symbols=IDR)).

This is a pricing estimate, not a quote and not a rental. Nothing was bought, signed up for or provisioned. Prices come from provider pages read on the date above and can change.

## Scope

The tiers below are for a limited, single-user Denyut: notes and reminders as commands, plus optional free-form chat through a model backend. Denyut has no browser or build automation today. These tiers are not equivalent to a general research, browsing and app-building assistant, and no feature or capability parity is claimed.

Free-form chat in Denyut needs a model backend: none (default), echo, or an OpenAI-compatible endpoint such as llama.cpp ([README](https://github.com/irvan-putra/denyut/blob/main/README.md)). The local Gemma work is preparation only. Phone compatibility and performance are unproven, and no model weights or inference have been tested.

## Options

All amounts are hosting only. They exclude the phone, its power and data plan, card or bank foreign-exchange fees, any domain, and any applicable Indonesian taxes. Tax treatment remains unverified; these are not all-in checkout totals.

| Option | Monthly hosting estimate | Notes |
| --- | --- | --- |
| Phone-local Gemma | Rp 0 extra hosting | Planned, unproven on the phone. Not the same capacity as a server. |
| Light always-on server, Hetzner CX23 (2 vCPU, 4 GB, 40 GB NVMe, 20 TB traffic) | about Rp 131,000 | Server EUR 5.99 (Rp 120,800). Worst case with IPv4 at EUR 0.50 is EUR 6.49 (Rp 130,900). Optional backups are 20% of the server price, about EUR 1.20 (Rp 24,200). |
| Light server in Jakarta, Biznet NEO Lite MS 4.2 (2 vCPU, 4 GB, 60 GB) | Rp 139,000 or more | List price. Not verified whether it includes PPN. Extra disk Rp 1,650/GB/month, snapshots Rp 1,500/GB/month. Shared bandwidth, 600 Mbps international. No per-GB egress charge found. |
| CPU server for a small model, Hetzner CAX41 (16 Arm vCPU, 32 GB, 320 GB) | Rp 837,000 to 847,000 | EUR 41.49, plus possible EUR 0.50 IPv4. The model sizing (a quantized model of about 7 to 8 billion parameters) is a guess. Speed is not measured and may be slow. |
| Fixed-price GPU server, Hetzner GEX45 (24 GB GPU, 64 GB RAM, 2 x 512 GB NVMe, Helsinki) | about Rp 4.32 million | EUR 214 a month including IPv4. One-time setup EUR 209 (Rp 4.21 million). First month EUR 423 (Rp 8.53 million). First 12 months EUR 2,777 (Rp 55.99 million). |

A rented GPU is a hosting choice for running a larger model. It may improve answers but does not guarantee it. RunPod describes a 24 GB card as suited to models up to roughly 13 billion parameters, but the real limit depends on quantization and context length.

Hourly cloud GPUs are not recommended for a no-surprise bill. They charge by the hour, including idle time. For scale, RunPod lists an RTX 4090 at USD 0.34 to 0.89 an hour, so a month left on is about Rp 4.5 to 11.9 million at 1 USD = Rp 18,245 (13 Nov 2026).

## Recommendation

Try phone-local Gemma first. Add a light always-on server only if reminders or the DeltaChat bot must run while the phone is off. Consider a fixed-price GPU only to run a larger model than the phone can, and plan for the first-month figure plus tax.

## Not verified

- Tax: Hetzner's VAT page does not list Indonesia and says other non-EU countries are invoiced without VAT, so Hetzner adds none ([source](https://docs.hetzner.com/general/billing-and-account-management/billing-at-hetzner/value-added-tax/), last changed 2026-09-15). Whether Indonesian VAT or self-assessment applies to the buyer is not verified ([tax office](https://pajak.go.id/en/digitaltax)). Biznet PPN is also not verified.
- Hetzner GEX45 traffic terms and minimum contract length.
- Hetzner price per extra TB of traffic. Traffic assumes ordinary text-only chat, excluding model downloads and build artifacts.
- Whether IPv4 is already included in the CX23 price.
- Card or bank foreign-exchange fees.
- Latency from Indonesia (not measured). The Hetzner GPU server is in Helsinki, its cloud servers are in Germany, Finland or Singapore, and Biznet is in Jakarta. Chat is asynchronous, so distance mostly adds delay to each reply.
- Model speed on any tier.

## Sources

- [Hetzner Cloud, cost-optimized](https://www.hetzner.com/cloud/cost-optimized/)
- [Hetzner cloud billing FAQ](https://docs.hetzner.com/cloud/billing/faq/)
- [Hetzner GEX45 GPU server](https://www.hetzner.com/dedicated-rootserver/matrix-gpu/)
- [Hetzner VAT by country](https://docs.hetzner.com/general/billing-and-account-management/billing-at-hetzner/value-added-tax/)
- [Biznet NEO Lite details and add-ons](https://kb.biznetgio.com/id_ID/getting-started/getting-started-neo-lite-dan-neo-lite-pro)
- [Biznet Gio price list](https://www.biznetgio.com/pricelist)
- [RunPod RTX 4090](https://www.runpod.io/gpu-models/rtx-4090)
- [Indonesian tax office, digital services](https://pajak.go.id/en/digitaltax)
- [Exchange rates, 13 Nov 2026](https://api.frankfurter.dev/v1/latest?base=EUR&symbols=IDR)
