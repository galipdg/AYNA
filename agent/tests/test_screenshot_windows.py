"""#54's capture against the real desktop: does it photograph the window, and is it fast enough?

The encoder's own tests are in `test_screenshot.py` and need no desktop. What needs one is
everything `capture_window_png` does around it: `PrintWindow` into a DIB, top-down pixel order,
and the crop from `GetWindowRect` to DWM's extended frame bounds. These are the assertions that
would have caught an upside-down image or a screenshot with 8 px of desktop down one side.

NFR-03 (< 300 ms per step) is measured here too, over the windows this session happens to have,
because the budget is only meaningful against a real frame.
"""

from __future__ import annotations

import sys
import time

import pytest

from ayna_agent.playback import screenshot as shot

pytestmark = pytest.mark.windows

if sys.platform != "win32":
    pytest.skip("windows-only module", allow_module_level=True)

# Imported below the skip: the module must not import the UIA backend off Windows.
from ayna_agent.recognition.frames import frame_bounds, window_rect
from ayna_agent.recognition.uia import UiaDesktop

#: NFR-03, `docs/rs/RS.md`: capturing a step's screenshot adds less than 300 ms to the step.
NFR_03_BUDGET_MS = 300


@pytest.fixture(scope="module")
def windows():
    backend = UiaDesktop()
    backend.setup()
    if not backend._ready:
        pytest.skip(f"no UI Automation here: {backend._unavailable}")
    try:
        found = backend.list_windows()
    finally:
        backend.close()
    if not found:
        pytest.skip("a session with no visible window has nothing to photograph")
    return found


@pytest.fixture(scope="module")
def one_window(windows):
    """The widest window on the desktop -- the one with the most to get wrong."""
    return max(windows, key=lambda w: w["bounds"][2] - w["bounds"][0])


def test_a_real_window_becomes_a_png_the_size_of_its_visible_frame(one_window):
    captured = shot.capture_window_png(one_window["handle"])

    left, top, right, bottom = frame_bounds(one_window["handle"])
    assert captured.width == right - left, one_window["title"]
    assert captured.height == bottom - top, one_window["title"]
    # The window's own reported bounds are the same rectangle, so the image matches the
    # geometry a step's candidates are expressed in (`uia.py` states this for #54 by name).
    assert [captured.width, captured.height] == [
        one_window["bounds"][2] - one_window["bounds"][0],
        one_window["bounds"][3] - one_window["bounds"][1],
    ]


def test_the_png_is_a_png_and_declares_the_captured_size(one_window):
    import struct

    captured = shot.capture_window_png(one_window["handle"])
    assert captured.png[:8] == b"\x89PNG\r\n\x1a\n"
    # IHDR is always the first chunk: 8 bytes of signature, 4 of length, 4 of type.
    width, height = struct.unpack(">II", captured.png[16:24])
    assert (width, height) == (captured.width, captured.height)
    assert len(captured.png) > 100, "a window's frame does not compress to nothing"


def test_the_capture_says_which_mechanism_read_it(one_window):
    captured = shot.capture_window_png(one_window["handle"])
    assert captured.captured_with in {"printWindow", "bitBlt"}


def test_the_image_is_not_upside_down(one_window):
    """A DIB is bottom-up unless its height is negative, and `_dib_bits` makes it negative.

    Checked against the screen itself rather than against a golden image: `GetPixel` at the
    window's top-left corner is, by definition, the colour of its first pixel row, so the first
    row of our buffer has to match it. Reverse the rows and this reads the window's bottom-left
    pixel instead and the assertion fails -- which is the bug this test exists for, and one that
    no amount of PNG-structure checking would notice.
    """
    handle = one_window["handle"]
    rect = window_rect(handle)
    width, height = rect[2] - rect[0], rect[3] - rect[1]
    top_down, _ = shot._capture_bgra(handle, width, height)

    rgb = shot.bgra_to_rgb(top_down)
    stride = width * 3
    rows = [rgb[i * stride : (i + 1) * stride] for i in range(height)]
    assert len(rows) == height
    # The window's first pixel row must be the first row of the buffer. `GetWindowRect`'s
    # origin is the top-left corner, and a screen read of that exact pixel is the same colour.
    import ctypes

    gdi32 = ctypes.WinDLL("gdi32")
    user32 = ctypes.WinDLL("user32")
    screen_dc = user32.GetDC(None)
    try:
        # GetPixel returns 0x00BBGGRR for the top-left corner of the window on screen.
        packed = gdi32.GetPixel(screen_dc, rect[0], rect[1])
    finally:
        user32.ReleaseDC(None, screen_dc)
    if packed == -1:
        pytest.skip("the window's top-left corner is off-screen")
    on_screen = bytes([packed & 0xFF, (packed >> 8) & 0xFF, (packed >> 16) & 0xFF])
    assert rows[0][:3] == on_screen, (
        "the first row of the buffer is not the window's top row: the DIB came back bottom-up"
    )


def test_capturing_a_window_stays_inside_the_nfr_03_budget(windows):
    """Every window on this desktop, so the number is not one lucky small frame."""
    slowest = 0.0
    worst = ""
    for window in windows:
        start = time.perf_counter()
        captured = shot.capture_window_png(window["handle"])
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > slowest:
            slowest, worst = (
                elapsed_ms,
                f"{window['title']} {captured.width}x{captured.height}",
            )
        assert elapsed_ms < NFR_03_BUDGET_MS, (
            f"{elapsed_ms:.0f} ms for {window['title']} "
            f"({captured.width}x{captured.height}), NFR-03 allows {NFR_03_BUDGET_MS}"
        )
    print(f"\nslowest capture: {slowest:.0f} ms ({worst})")


def test_a_handle_that_is_not_a_window_fails_instead_of_writing_a_file():
    with pytest.raises(Exception):  # noqa: B017 - win32 or CaptureFailed, both are a failure
        shot.capture_window_png(0x7FFFFFFF)


def test_the_taken_at_stamp_carries_an_offset_and_milliseconds(one_window):
    from datetime import datetime

    captured = shot.capture_window_png(one_window["handle"])
    parsed = datetime.fromisoformat(captured.taken_at)
    assert parsed.tzinfo is not None, captured.taken_at
    assert "." in captured.taken_at, f"no milliseconds in {captured.taken_at}"


def test_the_written_file_is_the_bytes_that_were_captured(one_window, tmp_path):
    captured = shot.capture_window_png(one_window["handle"])
    path = shot.write_step_png(tmp_path / "run-1", 2, captured.png)
    assert path.read_bytes() == captured.png
    assert path.name == "step-0002.png"
