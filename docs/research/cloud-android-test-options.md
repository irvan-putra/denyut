# Cloud options for testing an Android app on a real-architecture device

Status: prices and limits below were read from the vendors' public pages on 2026-11-16. They are list prices at that time, not a quote, and not a guarantee of capacity. Nothing was signed up for or run.

The question: where can an Android app be tested on an arm64 Android image or device without owning one? Three hosted options were looked at.

## Genymotion SaaS
- Pricing page: after subscribing, an organization pays $0.06 per minute for each active virtual device, billed minute by minute while the device runs. Prepaid cards are not supported. https://docs.genymotion.com/usage/saas/pricing/
- The recipes page says all official recipes use arm64 images. https://support.genymotion.com/hc/en-us/articles/360007473658-Which-virtual-devices-templates-official-recipes-are-available-for-Genymotion-SaaS
- Arithmetic from the listed rate: 20 active minutes is $1.20 before tax. That is not a spending cap. A device left running keeps billing, so an explicit stop is part of any run.
- Connecting with adb is covered at https://docs.genymotion.com/usage/saas/connect_adb/ (read on 2026-11-13, not re-read).

## Firebase Test Lab
- Spark (no cost) plan: up to 15 test runs per day in total, 10 on virtual devices and 5 on physical devices. Blaze: a daily no-cost allowance of 30 minutes on physical and 60 minutes on virtual devices, then $5 per hour per physical device and $1 per hour per virtual device, billed per minute rounded up. Budget alerts do not cap charges.
- The page says Test Lab is deprecated and will shut down on 2027-09-30, with a migration path to the Developer Device Platform on Google Cloud.
- Source: https://firebase.google.com/docs/test-lab/usage-quotas-pricing
- Which devices are available changes; see https://firebase.google.com/docs/test-lab/android/available-testing-devices . Availability there is not a reservation.

## AWS Device Farm
- Pay as you go: $0.17 per device minute. The page offers a one-time free trial of 1,000 device minutes "for a limited time" instead of the standard 250. https://aws.amazon.com/device-farm/pricing/
- The exact device list needs an AWS login, so which arm64 and API-level combinations are offered was not checked.

## Practical points
- All three need an account, and the paid routes need a payment method. The free tiers have daily or one-time limits.
- Use synthetic data only on shared hosted devices.
- Free local alternatives (an emulator, an owned device) avoid account and billing questions but need the right host CPU or virtualization support.
