# AOSP iptables: how interface negation prints, for scripts that parse rules

Status: source files read 2026-11-16 at the AOSP tag `android-14.0.0_r15` of `platform/external/iptables`. This reads source only. No device was tested, and what a given phone ships can differ from this tag.

## Interface columns
In `iptables/xshared.c`, `print_ifaces` builds each interface string by putting `!` directly in front of the interface name when the negation flag is set (`invflags & IPT_INV_VIA_IN` for input, `IPT_INV_VIA_OUT` for output), then prints it in the in/out column:

    snprintf(iface, IFNAMSIZ + 2, "%s%s", invflags & IPT_INV_VIA_IN ? "!" : "", ...

So a rule matching "not loopback" lists as one token, `!lo`, with no space after the `!`. A parser that splits on whitespace and expects `!` as its own token will miss it.
https://android.googlesource.com/platform/external/iptables/+/refs/tags/android-14.0.0_r15/iptables/xshared.c

## Which build is in the tree
The `iptables/Android.bp` at that tag lists `xtables-legacy-multi.c` among the sources of its command defaults, and the licence header lists GPL-2.0 among its SPDX kinds. I did not establish from this file alone whether the nft variant is built or shipped, or which one a device uses.
https://android.googlesource.com/platform/external/iptables/+/refs/tags/android-14.0.0_r15/iptables/Android.bp

## Scope
Plain reading of two files at one tag. The column spacing, other flags and IPv6 output were not checked.
