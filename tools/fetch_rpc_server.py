#!/usr/bin/env python3
"""Fetch the official deltachat-rpc-server Android binary from PyPI and
place it as an app asset.

Why: Chaquopy packs Python requirements into its own asset format and
silently drops extension-less executables, so the wheel's bundled binary
never reaches the APK. Shipping it as an explicit asset is deterministic.

Pinned version + sha256 (from pypi.org JSON API, 2026-11-15).
"""

import hashlib
import io
import sys
import urllib.request
import zipfile

URL = ("https://files.pythonhosted.org/packages/2c/a6/"
       "2ab49cf8c1c49a9dba5f62b36473e6c3f65d13ab1bec092160064639046e/"
       "deltachat_rpc_server-2.58.0-py3-none-android_21_arm64_v8a.whl")
SHA256 = "969f93476188a1f4110d6e895f55e4940deabf69c6079a878c20a4527515a000"
OUT = "android/app/src/main/jniLibs/arm64-v8a/librpcserver.so"


def main():
    data = urllib.request.urlopen(URL, timeout=120).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        sys.exit("sha256 mismatch: %s" % digest)
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = "deltachat_rpc_server/deltachat-rpc-server"
    binary = zf.read(name)
    with open(OUT, "wb") as fh:
        fh.write(binary)
    print("wrote %s (%d bytes, wheel sha256 verified)" % (OUT, len(binary)))


if __name__ == "__main__":
    main()
