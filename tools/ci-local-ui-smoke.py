#!/usr/bin/env python3
"""Account-free UI smoke for disabled local-model controls on a disposable emulator.

It launches MainActivity normally. It never starts the bot/self-test, configures
an account, opens a content provider, or loads/runs a model. PNGs are emitted as
marked chunks in the Actions log (no artifact upload/storage).
"""
from __future__ import annotations

import base64
import hashlib
import math
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
LAST_DUMP_ERROR = ""
SWIPES = 0
PHASE = "startup"
CURRENT_LABEL = ""
MAX_NO_PROGRESS_DUMPS = 2
TAP_TARGET_MIN_DP = 48
TAP_TARGET_MIN_PX = 48


def dump() -> ET.Element:
    global LAST_XML, LAST_DUMP_ERROR
    try:
        adb("shell", "uiautomator", "dump", "/sdcard/denyut-window.xml")
        LAST_XML = adb("shell", "cat", "/sdcard/denyut-window.xml")
        root = ET.fromstring(LAST_XML)
        LAST_DUMP_ERROR = ""
        return root
    except (subprocess.CalledProcessError, ET.ParseError, OSError) as error:
        LAST_DUMP_ERROR = f"{type(error).__name__}: {error}"
        raise


def emit_diagnostics(reason: str, label: str | None = None) -> None:
    """Failure-only evidence: stage, target, last parsed hierarchy, swipe count, display size."""
    target = label if label is not None else CURRENT_LABEL
    print(f"UI_DIAG_BEGIN phase={PHASE} label={target!r} reason={reason}", flush=True)
    if LAST_DUMP_ERROR:
        print(f"last_dump_error={LAST_DUMP_ERROR}", flush=True)
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



def wait_for_main_scroll_container(description: str, anchor: str,
                                   absent_dialog_labels: tuple[str, ...]) -> ET.Element:
    """Wait for dialog dismissal without assuming the retained list is at its top."""
    global CURRENT_LABEL
    CURRENT_LABEL = anchor
    deadline = time.monotonic() + 30.0
    last_error = ""
    while time.monotonic() < deadline:
        try:
            root = dump()
        except (subprocess.CalledProcessError, ET.ParseError, OSError) as error:
            last_error = f"{type(error).__name__}: {error}"
            time.sleep(0.5)
            continue
        scrollables = [node for node in root.iter("node")
                       if node.attrib.get("scrollable") == "true"]
        anchor_visible = bool(nodes(root, anchor))
        dialog_gone = all(not nodes(root, label) for label in absent_dialog_labels)
        # Modal screens can themselves be scrollable. Require the underlying app's
        # single list plus its retained-viewport anchor, and dialog-only labels gone.
        if len(scrollables) == 1 and anchor_visible and dialog_gone:
            return root
        time.sleep(0.5)
    reason = f"timed out after 30s waiting for main screen after {description}"
    if last_error:
        reason += f"; last hierarchy error: {last_error}"
    emit_diagnostics(reason, anchor)
    raise AssertionError(reason)

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


def minimum_tap_target_pixels(density_output: str) -> int:
    """Convert Android's 48dp minimum touch target to physical pixels."""
    overrides = re.findall(r"Override density:\s*(\d+)", density_output)
    physical = re.findall(r"Physical density:\s*(\d+)", density_output)
    values = overrides or physical
    if not values:
        raise AssertionError(f"Could not determine display density: {density_output!r}")
    dpi = int(values[-1])
    if not 80 <= dpi <= 1000:
        raise AssertionError(f"Implausible display density: {dpi}")
    return math.ceil(TAP_TARGET_MIN_DP * dpi / 160)


def tap_target_has_minimum_height(node: ET.Element) -> bool:
    _, top, _, bottom = parse_bounds(node)
    return bottom - top >= TAP_TARGET_MIN_PX


def parse_bounds(node: ET.Element) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
                         node.attrib.get("bounds", ""))
    if not match:
        raise AssertionError(f"Invalid bounds for {node.attrib.get('text', '')!r}")
    left, top, right, bottom = map(int, match.groups())
    if right <= left or bottom <= top:
        raise AssertionError(f"Non-positive bounds for {node.attrib.get('text', '')!r}")
    return left, top, right, bottom


def scroll_viewport(root: ET.Element) -> tuple[int, int, int, int]:
    scrollables = [node for node in root.iter("node")
                   if node.attrib.get("scrollable") == "true"]
    if len(scrollables) != 1:
        raise AssertionError(f"Expected one scrollable container, found {len(scrollables)}")
    return parse_bounds(scrollables[0])


def fully_in_scroll_viewport(root: ET.Element, node: ET.Element) -> bool:
    left, top, right, bottom = parse_bounds(node)
    view_left, view_top, view_right, view_bottom = scroll_viewport(root)
    # Android bounds are half-open: equality at the viewport edge is fully contained.
    # A clipped sliver is separately rejected by the minimum 48dp tap-target height.
    return (left >= view_left and right <= view_right
            and top >= view_top and bottom <= view_bottom)


def tap_node(node: ET.Element, root: ET.Element) -> None:
    left, top, right, bottom = parse_bounds(node)
    screen_nodes = [child for child in root.iter("node")]
    if not screen_nodes:
        raise AssertionError("No root view in current UI hierarchy")
    screen_left, screen_top, screen_right, screen_bottom = parse_bounds(screen_nodes[0])
    if (left < screen_left or top < screen_top
            or right > screen_right or bottom > screen_bottom):
        raise AssertionError(f"Refusing to tap clipped/off-screen control {node.attrib.get('text', '')!r}")
    for scrollable in (n for n in root.iter("node")
                       if n.attrib.get("scrollable") == "true"):
        if any(desc is node for desc in scrollable.iter("node")):
            if not fully_in_scroll_viewport(root, node):
                raise AssertionError(f"Refusing to tap clipped scroll control {node.attrib.get('text', '')!r}")
            break
    if not tap_target_has_minimum_height(node):
        emit_diagnostics(f"tap target is shorter than {TAP_TARGET_MIN_DP}dp", node.attrib.get("text", ""))
        raise AssertionError(f"Refusing to tap undersized target {node.attrib.get('text', '')!r}")
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


def set_phase(phase: str) -> None:
    global PHASE, CURRENT_LABEL
    PHASE = phase
    CURRENT_LABEL = ""


def swipe_scroll_container(root: ET.Element, direction: str = "down") -> None:
    """Swipe inside the live scrollable bounds, never at fixed screen pixels."""
    left, top, right, bottom = scroll_viewport(root)
    if right - left < 3 or bottom - top < 5:
        raise AssertionError("Scrollable container is too small for a swipe")
    x = left + (right - left) // 2
    quarter = (bottom - top) // 4
    if direction == "down":
        start_y, end_y = top + 3 * quarter, top + quarter
    elif direction == "up":
        start_y, end_y = top + quarter, top + 3 * quarter
    else:
        raise ValueError(f"Unknown scroll direction: {direction}")
    adb("shell", "input", "swipe", str(x), str(start_y), str(x), str(end_y), "350")


def matching_nodes(root: ET.Element, label: str, contains_fragment: bool) -> list[ET.Element]:
    if contains_fragment:
        return [node for node in root.iter("node")
                if label in node.attrib.get("text", "")
                or label in node.attrib.get("content-desc", "")]
    return nodes(root, label)


def scroll_until(label: str, *, require_fully_visible: bool = False,
                 contains_fragment: bool = False) -> ET.Element:
    """Find one control with bounded polling/scrolling; return its fresh hierarchy."""
    global SWIPES, CURRENT_LABEL
    CURRENT_LABEL = label
    deadline = time.monotonic() + 30.0
    previous_missing_xml: str | None = None
    no_progress = 0
    last_error = ""
    while time.monotonic() < deadline:
        try:
            root = dump()
        except (subprocess.CalledProcessError, ET.ParseError, OSError) as error:
            last_error = f"{type(error).__name__}: {error}"
            time.sleep(0.5)
            continue
        found = matching_nodes(root, label, contains_fragment)
        if found and (not require_fully_visible
                      or (fully_in_scroll_viewport(root, found[0])
                          and tap_target_has_minimum_height(found[0]))):
            return root
        signature = LAST_XML
        if signature == previous_missing_xml:
            no_progress += 1
            if no_progress >= MAX_NO_PROGRESS_DUMPS:
                reason = f"no scroll progress while seeking {label}"
                emit_diagnostics(reason, label)
                raise AssertionError(reason)
        else:
            no_progress = 0
        previous_missing_xml = signature
        try:
            swipe_scroll_container(root, "down")
        except AssertionError as error:
            emit_diagnostics(f"cannot scroll while seeking {label}: {error}", label)
            raise
        SWIPES += 1
        time.sleep(0.5)
    reason = f"scroll_until timed out after 30s: {label}"
    if last_error:
        reason += f"; last hierarchy error: {last_error}"
    emit_diagnostics(reason, label)
    raise AssertionError(f"UI control not reachable: {label}")


def is_at_scroll_top(root: ET.Element) -> bool:
    status_nodes = nodes(root, "Status: stopped")
    if not status_nodes:
        return False
    _, status_top, _, _ = parse_bounds(status_nodes[0])
    _, viewport_top, _, _ = scroll_viewport(root)
    return status_top == viewport_top


def reset_scroll_to_top() -> ET.Element:
    """Return the main list to its top using bounded, viewport-derived reverse swipes."""
    global SWIPES, CURRENT_LABEL
    CURRENT_LABEL = "Status: stopped at scroll origin"
    deadline = time.monotonic() + 30.0
    previous_xml: str | None = None
    no_progress = 0
    last_error = ""
    while time.monotonic() < deadline:
        try:
            root = dump()
        except (subprocess.CalledProcessError, ET.ParseError, OSError) as error:
            last_error = f"{type(error).__name__}: {error}"
            time.sleep(0.5)
            continue
        if is_at_scroll_top(root):
            CURRENT_LABEL = ""
            return root
        signature = LAST_XML
        if signature == previous_xml:
            no_progress += 1
            if no_progress >= MAX_NO_PROGRESS_DUMPS:
                reason = "no scroll progress while returning to top"
                emit_diagnostics(reason, "Status: stopped at scroll origin")
                raise AssertionError(reason)
        else:
            no_progress = 0
        previous_xml = signature
        try:
            swipe_scroll_container(root, "up")
        except AssertionError as error:
            emit_diagnostics(f"cannot reset scroll position: {error}", "Status: stopped at scroll origin")
            raise
        SWIPES += 1
        time.sleep(0.5)
    reason = "scroll-to-top timed out after 30s"
    if last_error:
        reason += f"; last hierarchy error: {last_error}"
    emit_diagnostics(reason, "Status: stopped at scroll origin")
    raise AssertionError(reason)


def tap_visible(label: str) -> None:
    """Seek, check, and tap from one fresh hierarchy while fully inside the viewport."""
    root = scroll_until(label, require_fully_visible=True)
    node = assert_text(root, label)
    if node.attrib.get("enabled") != "true":
        emit_diagnostics(f"tap target is not enabled: {label}", label)
        raise AssertionError(f"Tap target is not enabled: {label}")
    tap_node(node, root)


def assert_disabled(root: ET.Element, label: str) -> None:
    node = assert_text(root, label)
    if node.attrib.get("enabled") != "false":
        emit_diagnostics(f"{label} must remain disabled", label)
        raise AssertionError(f"{label} must remain disabled")


def inspect_disabled_controls(font_tag: str) -> None:
    """Check every control from a fresh viewport; never require co-visibility."""
    set_phase(f"{font_tag}-font disabled controls")
    reset_scroll_to_top()
    heading_root = scroll_until("Optional local Gemma (experimental)",
                                contains_fragment=True)
    assert_contains(heading_root, "Optional local Gemma (experimental)")
    # "Revoke model owner access" has no disabled state to assert, but it is
    # still sought so every local-model control gets an exposed-bounds
    # reachability check at each font scale.
    labels = ("Select existing verified owner contact", "Revoke model owner access",
              "Choose downloaded model file", "Load local model",
              "Unload local model", "Cancel file import")
    last_capture_xml: str | None = None
    for label in labels:
        CURRENT_LABEL = label
        root = scroll_until(label, require_fully_visible=True)
        assert_text(root, label)
        if label in ("Load local model", "Unload local model"):
            assert_disabled(root, label)
            if LAST_XML == last_capture_xml:
                # The accessibility hierarchy is unchanged since the previous
                # capture, so this capture may show the same viewport. Say so
                # in the log so a repeated-looking PNG is not misread as
                # independent evidence or a stalled scroll.
                print(f"NOTE: accessibility hierarchy unchanged; {label!r} "
                      "capture may show the same viewport", flush=True)
            last_capture_xml = LAST_XML
            screenshot(f"{label.lower().replace(' ', '-')}-disabled-{font_tag}-font")


def main() -> None:
    global TAP_TARGET_MIN_PX
    set_phase("startup")
    devices = adb("devices", "-l")
    print(devices, flush=True)
    if not any(line.startswith("emulator-") and "device" in line
               for line in devices.splitlines()[1:]):
        raise RuntimeError("Expected one running emulator")
    TAP_TARGET_MIN_PX = minimum_tap_target_pixels(adb("shell", "wm", "density"))

    # Launch normally: no autostart_bot or autosetup_bot extras.
    set_phase("normal-font launch")
    adb("shell", "am", "force-stop", PACKAGE)
    adb("shell", "am", "start", "-W", "-n", ACTIVITY)
    root = wait_for(lambda r: bool(nodes(r, "Start bot")), "main activity controls")
    for label in ("Start bot", "Stop bot", "Run self-test"):
        assert_text(root, label)
    screenshot("main-top-normal-font")
    # The list can be taller than one viewport, so this scroll-origin frame
    # can clip lower content. Whether that clipping is only capture position
    # is a pixel-review question: the harness separately checks each control's
    # exposed bounds and reachability, but an exposed >=48dp region can still
    # be the clipped portion of a taller control.
    print("NOTE: this scroll-origin frame can clip lower content; per-control "
          "exposed bounds/reachability are checked separately, pixels still need review",
          flush=True)

    # Inspect the disabled-model heading and each control in its own fresh viewport.
    inspect_disabled_controls("normal")

    # The owner picker is account-free because the bot is stopped; reacquire after reset.
    set_phase("normal-font owner picker")
    reset_scroll_to_top()
    tap_visible("Select existing verified owner contact")
    root = wait_for(lambda r: bool(nodes(r, "No eligible owner contact")),
                    "empty owner picker dialog")
    assert_contains(root, "This picker never creates accounts or pairs contacts.")
    screenshot("owner-picker-empty")
    tap_node(assert_text(root, "OK"), root)
    wait_for_main_scroll_container("owner picker", "Select existing verified owner contact",
                                   ("No eligible owner contact", "OK"))
    reset_scroll_to_top()

    # Inspect the warning, then cancel. Never press Choose file or open the system picker.
    set_phase("normal-font import warning")
    reset_scroll_to_top()
    tap_visible("Choose downloaded model file")
    root = wait_for(lambda r: bool(nodes(r, "Import 2.59 GB model file?")),
                    "file import warning dialog")
    assert_contains(root, "This app will not download it.")
    screenshot("import-confirmation")
    tap_node(assert_text(root, "Cancel"), root)
    wait_for_main_scroll_container("import warning", "Choose downloaded model file",
                                   ("Import 2.59 GB model file?", "Cancel"))
    reset_scroll_to_top()

    # The full versioned LiteRT license and generated third-party notice text is
    # bundled locally and reachable in-app; this path makes no network request.
    set_phase("normal-font bundled notices")
    reset_scroll_to_top()
    tap_visible("Third-party licenses and notices")
    root = wait_for(lambda r: bool(nodes(r, "Third-party licenses and notices"))
                    and contains(r, "LiteRT-LM Android API 0.19.1"),
                    "bundled LiteRT license text")
    assert_contains(root, "Apache License")
    screenshot("third-party-notices")
    tap_node(assert_text(root, "Close"), root)
    wait_for_main_scroll_container("notices dialog", "Third-party licenses and notices",
                                   ("LiteRT-LM Android API 0.19.1", "Apache License", "Close"))
    reset_scroll_to_top()

    # Larger font: reach the same labels independently; no co-visible-controls assumption.
    set_phase("large-font setup")
    adb("shell", "settings", "put", "system", "font_scale", "1.30")
    try:
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "am", "start", "-W", "-n", ACTIVITY)
        wait_for(lambda r: bool(nodes(r, "Start bot")), "main activity at large font")
        inspect_disabled_controls("large")
    finally:
        set_phase("restore normal font")
        adb("shell", "settings", "put", "system", "font_scale", "1.0")
    print("PASS: account-free UI smoke; disabled Load/Unload asserted in separate fresh viewports; "
          "bot not started, no accounts, provider selection, model, or network activity", flush=True)

if __name__ == "__main__":
    main()
