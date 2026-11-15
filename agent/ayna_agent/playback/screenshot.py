"""A PNG of the window under test, taken after every step (#54, FR-19).

The step result carries the *path* to the file, not the image: a 50-step run is about 15 MB of
PNG (`client/src/main/runs.ts`), and base64 inside a JSON-RPC notification would grow that by a
third and push it through the same socket as the live status. The agent and the client always
share a machine -- the client spawns the agent -- so a path is enough, and the client reads the
bytes and PUTs them to the server under #51's contract
(`PUT /api/runs/{runId}/results/{stepIndex}/screenshot`, raw `image/png`). Decided with the user
on 2026-11-15; `docs/agent-rpc.md` left the choice to this issue and #51.

Three things here are deliberate and cost something, so they are worth stating:

- **The crop rectangle is DWM's extended frame bounds**, `recognition.frames.frame_bounds`, which
  is what a person sees. `PrintWindow` renders the whole window rectangle, and since Windows 10
  that includes an invisible resize border -- 8 px of nothing on three sides, measured at 150 %
  in `frame_bounds`' own docstring. So the capture is at window-rectangle size and then cropped
  by the offset between the two rectangles; a screenshot that is 8 px of desktop on three sides
  is evidence of the wrong thing.
- **`PrintWindow` with `PW_RENDERFULLCONTENT`, not `BitBlt` of the screen.** `BitBlt` copies
  whatever is *on* the screen in that rectangle, so a dialog, a notification toast or the
  reviewer's own editor overlapping the app ends up in the test's evidence, and a window behind
  another window photographs as the window in front. `PrintWindow` asks the window to draw
  itself. It is not free of trouble -- some DirectX and hardware-accelerated surfaces come back
  black -- so `BitBlt` stays as the documented fallback, and :func:`capture_window_png` says
  which one answered.
- **No Pillow.** `pywin32` is already here through pywinauto and does the pixel capture;
  :func:`encode_png` writes the file with `zlib` and `struct`. That keeps the agent's dependency
  list where #52 froze it, and it makes the encoder a pure function that is tested on any OS.
  The cost is that the encoder is ours: it writes 8-bit truecolour, filter 0, no interlacing,
  which is the simplest PNG that every reader accepts.
"""

from __future__ import annotations

import logging
import struct
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ayna_agent.recognition.frames import frame_bounds, window_rect

log = logging.getLogger(__name__)

#: `PrintWindow` flag: render the window the way the compositor shows it, which is the only way
#: a themed or layered window comes back looking like itself.
PW_RENDERFULLCONTENT = 0x00000002

#: zlib level for the image data. **Not the default 6.** NFR-03 gives the whole screenshot
#: 300 ms per step, and compression is the only part of this module that grows with the window:
#: level 6 on a 1920x1080 frame is the difference between meeting that budget and missing it,
#: while level 1 gives up some size on an image nobody stores for long (the server keeps the
#: newest 1000 runs). Measured in `tests/test_screenshot.py::test_encoding_a_full_hd_frame_is_fast`.
_COMPRESS_LEVEL = 1

#: 8-bit truecolour, no alpha. A screenshot has nothing transparent in it, and three bytes per
#: pixel instead of four is a quarter less to compress.
_COLOUR_TYPE_RGB = 2
_BIT_DEPTH = 8

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class CaptureFailed(Exception):
    """The window is there, but no image could be read from it."""


@dataclass(frozen=True)
class Screenshot:
    """One captured image and the facts the run report needs about it."""

    png: bytes
    width: int
    height: int
    #: `"printWindow"` or `"bitBlt"` -- which mechanism produced the pixels. Recorded because a
    #: `bitBlt` image may contain windows that are not the application under test, and a
    #: reviewer of a surprising screenshot should not have to guess.
    captured_with: str
    #: When the image was taken, ISO 8601 with a UTC offset. To the millisecond, not the second
    #: that `recognition/snapshot.py` uses for `startedAt`: steps are faster than a second, and
    #: the approval screen's question is how much older the image is than the geometry
    #: (`docs/agent-rpc.md`), which a one-second resolution cannot answer.
    taken_at: str


def _chunk(kind: bytes, data: bytes) -> bytes:
    """One PNG chunk: length, type, data, CRC over type and data."""
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def encode_png(width: int, height: int, rgb: bytes) -> bytes:
    """`width * height` RGB triples, row-major and top-down, as a PNG file.

    Pure: no Windows, no files, no clock. This is where the tests live, because everything that
    can be wrong about a PNG can be wrong here, and nothing that can be wrong about it needs a
    desktop to find.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"a PNG is at least 1x1, not {width}x{height}")
    expected = width * height * 3
    if len(rgb) != expected:
        raise ValueError(f"{width}x{height} RGB needs {expected} bytes, got {len(rgb)}")

    header = struct.pack(
        ">IIBBBBB", width, height, _BIT_DEPTH, _COLOUR_TYPE_RGB, 0, 0, 0
    )
    # Every scanline is prefixed with its filter type. 0 is "none": the other filters predict a
    # byte from its neighbours and compress better, but they cost a pass over the image in
    # Python, and the budget above is the reason not to.
    stride = width * 3
    raw = bytearray()
    for start in range(0, len(rgb), stride):
        raw += b"\x00"
        raw += rgb[start : start + stride]

    return (
        _PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), _COMPRESS_LEVEL))
        + _chunk(b"IEND", b"")
    )


def bgra_to_rgb(bgra: bytes) -> bytes:
    """Drop the alpha byte and swap to RGB.

    Windows hands out 32-bit bitmaps as BGRA; the alpha byte of a `PrintWindow` capture is not
    meaningful (it is 0 for most of the frame), so keeping it would make a fully transparent
    PNG of a perfectly good screenshot.
    """
    if len(bgra) % 4:
        raise ValueError(f"BGRA is four bytes a pixel, got {len(bgra)}")
    pixels = bytearray(len(bgra) // 4 * 3)
    pixels[0::3] = bgra[2::4]
    pixels[1::3] = bgra[1::4]
    pixels[2::3] = bgra[0::4]
    return bytes(pixels)


def crop_rgb(
    rgb: bytes, width: int, height: int, box: tuple[int, int, int, int]
) -> tuple[int, int, bytes]:
    """`(left, top, right, bottom)` of an RGB buffer, clamped to it.

    Clamped rather than checked: the two rectangles this reconciles come from different Windows
    APIs read a moment apart, so a window that moved between them can put the crop one pixel
    outside the capture. A screenshot short of a pixel is worth having; an exception in the
    middle of a passing step is not.
    """
    left, top, right, bottom = box
    left = max(0, min(left, width))
    top = max(0, min(top, height))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))

    stride = width * 3
    out = bytearray()
    for row in range(top, bottom):
        start = row * stride + left * 3
        out += rgb[start : start + (right - left) * 3]
    return right - left, bottom - top, bytes(out)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def capture_window_png(handle: int, *, now: object = None) -> Screenshot:
    """The window as a PNG, cropped to the rectangle a person sees. Windows only.

    `now` is for the tests; it takes no argument and returns the ISO string to record.
    """
    stamp = _now() if now is None else now()  # type: ignore[operator]
    window = window_rect(handle)
    frame = frame_bounds(handle)
    width = window[2] - window[0]
    height = window[3] - window[1]
    if width <= 0 or height <= 0:
        raise CaptureFailed(f"window {handle} has no area: {window}")

    bgra, captured_with = _capture_bgra(handle, width, height)
    rgb = bgra_to_rgb(bgra)
    # Both rectangles are in physical pixels in virtual-desktop coordinates (the agent is
    # per-monitor-v2 DPI aware), so the offset between them is the crop and no scaling is
    # involved. `recognition/uia.py` states that assumption for this issue by name.
    box = (
        frame[0] - window[0],
        frame[1] - window[1],
        frame[2] - window[0],
        frame[3] - window[1],
    )
    cropped_width, cropped_height, cropped = crop_rgb(rgb, width, height, box)
    return Screenshot(
        png=encode_png(cropped_width, cropped_height, cropped),
        width=cropped_width,
        height=cropped_height,
        captured_with=captured_with,
        taken_at=stamp,
    )


def _capture_bgra(handle: int, width: int, height: int) -> tuple[bytes, str]:
    """`width * height` BGRA pixels of the whole window rectangle, top-down.

    Top-down is not the default: a DIB is bottom-up unless its height is given as negative,
    and a screenshot that is upside down is a bug nobody expects to look for.
    """
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.WinDLL("user32")
    gdi32 = ctypes.WinDLL("gdi32")

    window_dc = user32.GetWindowDC(ctypes.wintypes.HWND(handle))
    if not window_dc:
        raise CaptureFailed(f"no device context for window {handle}")
    memory_dc = None
    bitmap = None
    try:
        memory_dc = gdi32.CreateCompatibleDC(window_dc)
        bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
        if not memory_dc or not bitmap:
            raise CaptureFailed("could not allocate a bitmap for the capture")
        gdi32.SelectObject(memory_dc, bitmap)

        captured_with = "printWindow"
        if not user32.PrintWindow(
            ctypes.wintypes.HWND(handle),
            memory_dc,
            ctypes.c_uint(PW_RENDERFULLCONTENT),
        ):
            # Whatever is on the screen there, overlapping windows and all. See the module
            # docstring: worse evidence, but evidence.
            if not gdi32.BitBlt(
                memory_dc, 0, 0, width, height, window_dc, 0, 0, 0x00CC0020
            ):
                raise CaptureFailed(
                    f"neither PrintWindow nor BitBlt could read window {handle}"
                )
            captured_with = "bitBlt"

        return _dib_bits(gdi32, memory_dc, bitmap, width, height), captured_with
    finally:
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(ctypes.wintypes.HWND(handle), window_dc)


def _dib_bits(
    gdi32: object, memory_dc: int, bitmap: int, width: int, height: int
) -> bytes:
    """`GetDIBits` into a buffer, 32 bits a pixel, top-down."""
    import ctypes

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            # Negative: top-down. See `_capture_bgra`.
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0  # BI_RGB

    buffer = ctypes.create_string_buffer(width * height * 4)
    rows = gdi32.GetDIBits(  # type: ignore[attr-defined]
        memory_dc,
        bitmap,
        0,
        ctypes.c_uint(height),
        buffer,
        ctypes.byref(header),
        0,  # DIB_RGB_COLORS
    )
    if rows != height:
        raise CaptureFailed(f"GetDIBits read {rows} of {height} rows")
    return buffer.raw


def step_png_path(run_directory: Path | str, step_index: int) -> Path:
    """Where one step's PNG goes.

    Zero-padded so a directory listing is in step order, and named by `stepIndex` because that
    is the only identifier the server's upload path has
    (`PUT /api/runs/{runId}/results/{stepIndex}/screenshot`).
    """
    return Path(run_directory) / f"step-{step_index:04d}.png"


def write_step_png(run_directory: Path | str, step_index: int, png: bytes) -> Path:
    """Write the PNG and return its path, creating the run's directory if it is not there."""
    path = step_png_path(run_directory, step_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


@dataclass(frozen=True)
class StepImage:
    """What one step's result says about its screenshot: where it is, and when it was taken."""

    #: Absolute path to the PNG on the machine the agent runs on. The client reads it from
    #: there; see the module docstring for why the bytes do not travel in the result.
    path: str
    taken_at: str
    width: int
    height: int
    captured_with: str


#: `(stepIndex) -> StepImage or None`. What :func:`step_capture` builds and the runner calls
#: after each step it ran. `None` means "no image for this step", never an exception.
StepCapture = Callable[[int], "StepImage | None"]


def step_capture(
    handle: int,
    run_directory: Path | str,
    *,
    capture: Callable[[int], Screenshot] = capture_window_png,
) -> StepCapture:
    """The per-step capture the runner calls, bound to one window and one run's directory.

    **A capture that fails must never fail the step.** The most valuable screenshot in a run is
    the one of the step that just failed, and the commonest reason a step fails is that the
    window is not what the test expected -- including gone. Raising here would turn "the step
    failed and here is why" into "the run blew up in the screenshot code", so a failure is
    logged and the step keeps its own result with no image. #59's report and the client must
    therefore treat a missing screenshot as normal, not as an error.
    """

    def take(step_index: int) -> StepImage | None:
        try:
            shot = capture(handle)
            path = write_step_png(run_directory, step_index, shot.png)
        # Broad on purpose: see the docstring. A capture must never fail the step, and a
        # dying UIA provider raises a COMError, not CaptureFailed.
        except Exception:
            log.warning(
                "no screenshot for step %d of window %#x",
                step_index,
                handle,
                exc_info=True,
            )
            return None
        return StepImage(
            path=str(path),
            taken_at=shot.taken_at,
            width=shot.width,
            height=shot.height,
            captured_with=shot.captured_with,
        )

    return take


#: Where a run's PNGs go when the caller names no directory: one directory per run under the
#: system temporary directory. **Nothing here deletes them.** The agent cannot know when the
#: client has finished uploading a run's images (#51), so cleanup belongs to whoever owns the
#: run -- the client already removes report files for the same reason
#: (`client/src/main/index.ts`). Raised with omer for #51/#59.
SCREENSHOT_ROOT = "ayna-screenshots"


def new_run_directory(
    root: Path | str | None = None, *, moment: datetime | None = None
) -> Path:
    """A fresh directory for one run's step PNGs, named so runs sort by when they started.

    Not created here: `write_step_png` makes it on the first image, so a run whose every
    capture failed leaves nothing behind.
    """
    import tempfile

    base = (
        Path(root)
        if root is not None
        else Path(tempfile.gettempdir()) / SCREENSHOT_ROOT
    )
    stamp = (moment or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    return base / f"run-{stamp}"
