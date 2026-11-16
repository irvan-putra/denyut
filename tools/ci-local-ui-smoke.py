#!/usr/bin/env python3
"""Account-free UI smoke for disabled local-model controls on a disposable emulator.

It launches MainActivity normally. It never starts the bot/self-test, configures
an account, opens a content provider, or loads/runs a model. PNGs are emitted as
marked chunks in the Actions log (no artifact upload/storage).
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "com.vanipy.denyut"
ACTIVITY = f"{PACKAGE}/.MainActivity"
OUT = Path(os.environ.get("DENYUT_UI_OUTPUT", "ui-evidence"))
OUT.mkdir(parents=True, exist_ok=True)


def adb(*args: str) -> str:
    p = subprocess.run(["adb", *args], check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    return p.stdout.strip()


LAST_XML = ""
SWIPES = 0


def dump() -> ET.Element:
    global LAST_XML
    adb("shell", "uiautomator", "dump", "/sdcard/denyut-window.xml")
    LAST_XML = adb("shell", "cat", "/sdcard/denyut-window.xml")
    return ET.fromstring(LAST_XML)


def emit_diagnostics(reason: str) -> None:
    """Failure-only evidence in the log (no artifact, no new assertion): the last hierarchy this script parsed,
    the swipe count and the display size. The app is account-free and shows only fixed text."""
    print(f"UI_DIAG_BEGIN {reason}", flush=True)
    print(f"swipes_so_far={SWIPES}", flush=True)
    for cmd in (("wm", "size"), ("wm", "density")):
        try:
            print(adb("shell", *cmd), flush=True)
        except Exception as error:  # diagnostics must never mask the real failure
            print(f"{cmd}: {error}", flush=True)
    print("UI_DIAG_XML_BEGIN", flush=True)
    print(LAST_XML, flush=True)
    print("UI_DIAG_XML_END", flush=True)
    print("UI_DIAG_END", flush=True)


def wait_for(predicate, description: str, timeout: float = 30.0) -> ET.Element:
    """Poll the actual accessibility tree; emulator/UI startup can be slow."""
    deadline = time.monotonic() + timeout
    last_error = "UI has not reached the expected state"
    while time.monotonic() < deadline:
        try:
            root = dump()
            if predicate(root):
                return root
        except (subprocess.CalledProcessError, ET.ParseError) as error:
            last_error = str(error)
        time.sleep(0.5)
    raise AssertionError(f"Timed out waiting for {description}: {last_error}")


def nodes(root: ET.Element, text: str) -> list[ET.Element]:
    return [n for n in root.iter("node") if n.attrib.get("text", "").strip() == text]


def assert_text(root: ET.Element, text: str) -> ET.Element:
    found = nodes(root, text)
    if not found:
        emit_diagnostics(f"text not found: {text}")
        raise AssertionError(f"Expected visible text not found: {text}")
    return found[0]


def contains(root: ET.Element, fragment: str) -> bool:
    return any(fragment in node.attrib.get("text", "")
               or fragment in node.attrib.get("content-desc", "")
               for node in root.iter("node"))


def assert_contains(root: ET.Element, fragment: str) -> ET.Element:
    for node in root.iter("node"):
        if fragment in node.attrib.get("text", "") or fragment in node.attrib.get("content-desc", ""):
            return node
    emit_diagnostics(f"fragment not found: {fragment}")
    raise AssertionError(f"Expected visible text fragment not found: {fragment}")


def tap_node(node: ET.Element) -> None:
    pieces = node.attrib["bounds"].split("][")
    left, top = map(int, pieces[0].strip("[]").split(","))
    right, bottom = map(int, pieces[1].strip("[]").split(","))
    adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
    time.sleep(0.8)


def screenshot(name: str) -> None:
    path = OUT / f"{name}.png"
    with path.open("wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], check=True,
                       stdout=f, stderr=subprocess.PIPE)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    encoded = base64.b64encode(data).decode("ascii")
    width = 6000
    chunks = [encoded[i:i + width] for i in range(0, len(encoded), width)]
    print(f"SCREENSHOT_BEGIN {path.name} {len(data)} {digest} {len(chunks)}", flush=True)
    for index, chunk in enumerate(chunks, 1):
        print(f"SCREENSHOT_CHUNK {path.name} {index}/{len(chunks)} {chunk}", flush=True)
    print(f"SCREENSHOT_END {path.name}", flush=True)


def swipe_scroll_container(root: ET.Element) -> None:
    """Swipe inside the live scrollable bounds, never at fixed screen pixels."""
    scrollables = [node for node in root.iter("node")
                   if node.attrib.get("scrollable") == "true"]
    if len(scrollables) != 1:
        raise AssertionError(f"Expected one scrollable container, found {len(scrollables)}")
    coords = [int(value) for value in re.findall(r"-?\d+", scrollables[0].attrib.get("bounds", ""))]
    if len(coords) != 4:
        raise AssertionError("Invalid scrollable container bounds")
    left, top, right, bottom = coords
    if right - left < 3 or bottom - top < 5:
        raise AssertionError("Scrollable container is too small for a swipe")
    x = left + (right - left) // 2
    start_y = top + 3 * (bottom - top) // 4
    end_y = top + (bottom - top) // 4
    adb("shell", "input", "swipe", str(x), str(start_y), str(x), str(end_y), "350")


def scroll_until(label: str) -> ET.Element:
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        try:
            root = dump()
        except (subprocess.CalledProcessError, ET.ParseError):
            time.sleep(0.5)
            continue
        found = nodes(root, label)
        if found:
            return root
        swipe_scroll_container(root)
        global SWIPES
        SWIPES += 1
        time.sleep(0.5)
    emit_diagnostics(f"scroll_until timed out: {label}")
    raise AssertionError(f"UI control not reachable by polling/scrolling: {label}")


def main() -> None:
    devices = adb("devices", "-l")
    print(devices, flush=True)
    if not any(line.startswith("emulator-") and "device" in line
               for line in devices.splitlines()[1:]):
        raise RuntimeError("Expected one running emulator")

    # Launch normally: no autostart_bot or autosetup_bot extras.
    adb("shell", "am", "force-stop", PACKAGE)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY)
    root = wait_for(lambda r: bool(nodes(r, "Start bot")), "main activity controls")
    for label in ("Start bot", "Stop bot", "Run self-test"):
        assert_text(root, label)
    screenshot("main-top-normal-font")

    # Reach the new controls and verify both activation actions stay disabled.
    root = scroll_until("Load local model")
    assert_contains(root, "Optional local Gemma (experimental)")
    for label in ("Select existing verified owner contact", "Choose downloaded model file",
                  "Unload local model", "Cancel file import"):
        assert_text(root, label)
    if assert_text(root, "Load local model").attrib.get("enabled") != "false":
        raise AssertionError("Load must stay disabled before import/activation")
    if assert_text(root, "Unload local model").attrib.get("enabled") != "false":
        raise AssertionError("Unload must stay disabled before import/activation")
    screenshot("controls-normal-font")

    # Bot is not running, so the owner query returns the empty state without RPC/account access.
    tap_node(assert_text(root, "Select existing verified owner contact"))
    root = wait_for(lambda r: bool(nodes(r, "No eligible owner contact")), "empty owner picker dialog")
    assert_contains(root, "This picker never creates accounts or pairs contacts.")
    screenshot("owner-picker-empty")
    tap_node(assert_text(root, "OK"))

    # Inspect the warning, then cancel. Never press Choose file or open the system picker.
    root = scroll_until("Choose downloaded model file")
    tap_node(assert_text(root, "Choose downloaded model file"))
    root = wait_for(lambda r: bool(nodes(r, "Import 2.59 GB model file?")), "file import warning dialog")
    assert_contains(root, "This app will not download it.")
    screenshot("import-confirmation")
    tap_node(assert_text(root, "Cancel"))
    wait_for(lambda r: bool(nodes(r, "Choose downloaded model file")), "dismissed import dialog")

    # The full versioned LiteRT license and generated third-party notice text is
    # bundled locally and reachable in-app; this path makes no network request.
    root = scroll_until("Third-party licenses and notices")
    tap_node(assert_text(root, "Third-party licenses and notices"))
    root = wait_for(lambda r: bool(nodes(r, "Third-party licenses and notices"))
                    and contains(r, "LiteRT-LM Android API 0.19.1"),
                    "bundled LiteRT license text")
    assert_contains(root, "Apache License")
    screenshot("third-party-notices")
    tap_node(assert_text(root, "Close"))
    wait_for(lambda r: bool(nodes(r, "Third-party licenses and notices")), "dismissed notices dialog")

    # Larger font: verify key controls remain reachable and the two activation buttons stay disabled.
    adb("shell", "settings", "put", "system", "font_scale", "1.30")
    try:
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "am", "start", "-W", "-n", ACTIVITY)
        root = scroll_until("Load local model")
        for label in ("Select existing verified owner contact", "Choose downloaded model file",
                      "Load local model", "Unload local model", "Cancel file import"):
            assert_text(root, label)
        if assert_text(root, "Load local model").attrib.get("enabled") != "false":
            raise AssertionError("Load must remain disabled at large font scale")
        if assert_text(root, "Unload local model").attrib.get("enabled") != "false":
            raise AssertionError("Unload must remain disabled at large font scale")
        screenshot("controls-large-font")
    finally:
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
    print("PASS: disabled-state UI smoke; bot not started, no accounts, provider selection, model, or network activity", flush=True)

if __name__ == "__main__":
    main()
