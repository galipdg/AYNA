"""#54's screenshot: the PNG encoder, the crop and the file layout.

The encoder is a pure function, so everything that can be wrong about the file we write is
tested here with no desktop: the bytes are read back with `zlib` and `struct` rather than
compared with a golden file, because a golden PNG would pass for the wrong reason the moment
the compression level changes.

The capture itself (`capture_window_png`) needs a real window and lives in
`test_screenshot_windows.py`.
"""

from __future__ import annotations

import struct
import time
import zlib

import pytest

from ayna_agent.playback import screenshot as shot

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    """Every chunk of a PNG as `(type, data)`, checking each CRC on the way."""
    assert png[:8] == _SIGNATURE
    out: list[tuple[bytes, bytes]] = []
    at = 8
    while at < len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        kind = png[at + 4 : at + 8]
        data = png[at + 8 : at + 8 + length]
        (crc,) = struct.unpack(">I", png[at + 8 + length : at + 12 + length])
        assert crc == zlib.crc32(kind + data) & 0xFFFFFFFF, f"bad CRC on {kind!r}"
        out.append((kind, data))
        at += 12 + length
    return out


def decode(png: bytes) -> tuple[int, int, bytes]:
    """`(width, height, RGB bytes)` read back out of our own PNG."""
    found = dict(chunks(png))
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", found[b"IHDR"]
    )
    assert (depth, colour, compression, filtering, interlace) == (8, 2, 0, 0, 0)
    raw = zlib.decompress(found[b"IDAT"])
    stride = width * 3
    rgb = bytearray()
    for row in range(height):
        start = row * (stride + 1)
        assert raw[start] == 0, "every scanline is filter 0"
        rgb += raw[start + 1 : start + 1 + stride]
    return width, height, bytes(rgb)


def test_a_one_pixel_png_round_trips():
    png = shot.encode_png(1, 1, b"\x10\x20\x30")
    assert decode(png) == (1, 1, b"\x10\x20\x30")


def test_the_chunks_are_the_four_a_reader_expects_in_order():
    png = shot.encode_png(2, 2, bytes(12))
    assert [kind for kind, _ in chunks(png)] == [b"IHDR", b"IDAT", b"IEND"]


def test_pixels_keep_their_row_order_and_their_colours():
    # Two rows that cannot be confused with each other: red over blue. A bottom-up DIB or a
    # BGR swap both show up here and nowhere else.
    rgb = b"\xff\x00\x00" * 3 + b"\x00\x00\xff" * 3
    width, height, out = decode(shot.encode_png(3, 2, rgb))
    assert (width, height) == (3, 2)
    assert out[:9] == b"\xff\x00\x00" * 3
    assert out[9:] == b"\x00\x00\xff" * 3


def test_the_encoder_refuses_a_buffer_that_is_not_the_stated_size():
    with pytest.raises(ValueError, match="needs 12 bytes, got 11"):
        shot.encode_png(2, 2, bytes(11))


@pytest.mark.parametrize("size", [(0, 1), (1, 0), (-1, 4)])
def test_the_encoder_refuses_an_empty_image(size):
    with pytest.raises(ValueError, match="at least 1x1"):
        shot.encode_png(size[0], size[1], b"")


def test_bgra_becomes_rgb_and_the_alpha_byte_is_dropped():
    # One pixel: B=1, G=2, R=3, A=255 -> R=3, G=2, B=1.
    assert shot.bgra_to_rgb(bytes([1, 2, 3, 255])) == bytes([3, 2, 1])


def test_bgra_with_a_trailing_part_pixel_is_refused():
    with pytest.raises(ValueError, match="four bytes a pixel"):
        shot.bgra_to_rgb(bytes(7))


def test_a_transparent_alpha_does_not_make_the_pixels_transparent():
    """`PrintWindow` leaves alpha at 0 over most of the frame; the PNG must not carry it."""
    png = shot.encode_png(1, 1, shot.bgra_to_rgb(bytes([9, 8, 7, 0])))
    assert decode(png) == (1, 1, bytes([7, 8, 9]))


def grid(width: int, height: int) -> bytes:
    """An image whose every pixel says where it is: `(x, y, 0)`."""
    return bytes(
        value for y in range(height) for x in range(width) for value in (x, y, 0)
    )


def test_a_crop_takes_the_rectangle_it_was_given():
    width, height, out = shot.crop_rgb(grid(8, 6), 8, 6, (2, 1, 5, 4))
    assert (width, height) == (3, 3)
    # Top-left of the crop is (2, 1) of the original, bottom-right is (4, 3).
    assert out[:3] == bytes([2, 1, 0])
    assert out[-3:] == bytes([4, 3, 0])


def test_a_crop_of_the_whole_image_changes_nothing():
    pixels = grid(4, 3)
    assert shot.crop_rgb(pixels, 4, 3, (0, 0, 4, 3)) == (4, 3, pixels)


def test_a_crop_reaching_past_the_image_is_clamped_not_an_error():
    """The window rectangle and the frame bounds are read a moment apart (see the module)."""
    width, height, out = shot.crop_rgb(grid(4, 3), 4, 3, (-5, -5, 99, 99))
    assert (width, height) == (4, 3)
    assert out == grid(4, 3)


def test_a_crop_with_no_area_still_yields_a_pixel():
    width, height, _ = shot.crop_rgb(grid(4, 3), 4, 3, (2, 2, 2, 2))
    assert (width, height) == (1, 1)


def test_the_frame_offset_of_a_windows_10_border_is_what_gets_cropped():
    """The case `frame_bounds` measured: 8 px of invisible border left, right and bottom.

    A 472x261 window rectangle holding a 456x253 visible frame at offset (8, 0).
    """
    width, height, _ = shot.crop_rgb(grid(100, 60), 100, 60, (8, 0, 92, 52))
    assert (width, height) == (84, 52)


def test_step_png_paths_sort_in_step_order(tmp_path):
    names = [shot.step_png_path(tmp_path, i).name for i in (0, 2, 10, 100)]
    assert names == sorted(names), names
    assert names[0] == "step-0000.png"


def test_writing_a_step_png_creates_the_run_directory(tmp_path):
    target = tmp_path / "run-7" / "nested"
    path = shot.write_step_png(target, 3, b"not really a png")
    assert path == target / "step-0003.png"
    assert path.read_bytes() == b"not really a png"


def full_hd_app_frame() -> bytes:
    """1920x1080 shaped like an application window: flat ground, a title bar, rows of text.

    This, not random noise, is what the budget has to hold for. A screenshot of a form is
    mostly one colour, and that is exactly what a compressor is good at.
    """
    rows = []
    for y in range(1080):
        if y < 40:
            rows.append(bytes([240, 240, 240]) * 1920)
        elif y % 23 == 0:
            rows.append(bytes([255, 255, 255]) * 960 + bytes([30, 30, 30]) * 960)
        else:
            rows.append(bytes([255, 255, 255]) * 1920)
    return b"".join(rows)


def encode_ms(width: int, height: int, pixels: bytes) -> tuple[float, bytes]:
    start = time.perf_counter()
    png = shot.encode_png(width, height, pixels)
    return (time.perf_counter() - start) * 1000, png


def test_encoding_a_realistic_full_hd_frame_is_a_small_part_of_the_budget():
    """NFR-03 gives the whole step 300 ms, and the encoder may not be most of it.

    Measured on this machine (2026-11-15): 29 ms and a 30 KiB file for the frame below, where
    a real 1920x1020 window captured end to end took 96 ms
    (`test_screenshot_windows.py::test_capturing_a_window_stays_inside_the_nfr_03_budget`).
    The bound here is generous against a shared CI runner but still catches the changes worth
    catching -- a higher zlib level or a per-row filter costs several times this.
    """
    elapsed_ms, png = encode_ms(1920, 1080, full_hd_app_frame())
    assert png[:8] == _SIGNATURE
    assert elapsed_ms < 100, f"encoding took {elapsed_ms:.0f} ms"


def test_an_incompressible_frame_is_the_one_case_with_no_budget_left():
    """The pathological bound, kept as a measurement rather than a promise.

    Random noise is what a compressor can do nothing with: 226-295 ms and a 6 MB file on this
    machine, against 29 ms and 30 KiB for the app frame above. So NFR-03 holds comfortably for
    the windows AYNA tests and has **no margin** for a window whose content is genuinely
    incompressible -- a full-screen photo, a video surface, a gradient-heavy canvas. The
    assertion is loose on purpose: it guards against an order-of-magnitude regression, and the
    real finding belongs in the task note, not in a number this test pretends to defend.
    """
    import random

    rng = random.Random(42)
    pixels = bytes(rng.getrandbits(8) for _ in range(1920 * 1080 * 3))
    elapsed_ms, png = encode_ms(1920, 1080, pixels)
    assert png[:8] == _SIGNATURE
    assert elapsed_ms < 1000, f"encoding noise took {elapsed_ms:.0f} ms"


# --- the per-step capture the runner calls -------------------------------------------------


def a_screenshot(png: bytes = b"png-bytes") -> shot.Screenshot:
    return shot.Screenshot(
        png=png,
        width=800,
        height=600,
        captured_with="printWindow",
        taken_at="2026-11-15T14:03:11.250+03:00",
    )


def test_the_capture_writes_the_file_and_describes_it(tmp_path):
    take = shot.step_capture(0x1234, tmp_path, capture=lambda handle: a_screenshot())

    image = take(5)

    assert image is not None
    assert image.path == str(tmp_path / "step-0005.png")
    assert (tmp_path / "step-0005.png").read_bytes() == b"png-bytes"
    assert (image.width, image.height) == (800, 600)
    assert image.captured_with == "printWindow"
    assert image.taken_at == "2026-11-15T14:03:11.250+03:00"


def test_the_capture_is_bound_to_the_handle_it_was_built_with(tmp_path):
    seen = []

    def capture(handle):
        seen.append(handle)
        return a_screenshot()

    take = shot.step_capture(0xABCD, tmp_path, capture=capture)
    take(0)
    take(1)
    assert seen == [0xABCD, 0xABCD]


def test_a_capture_that_raises_returns_no_image_rather_than_failing_the_step(
    tmp_path, caplog
):
    """The window is often gone exactly when the step failed; that must not raise here."""

    def capture(handle):
        raise shot.CaptureFailed("the window closed")

    take = shot.step_capture(0x1234, tmp_path, capture=capture)

    with caplog.at_level("WARNING"):
        assert take(2) is None
    assert "no screenshot for step 2" in caplog.text
    assert not list(tmp_path.iterdir()), "no half-written file is left behind"


def test_a_capture_that_cannot_be_written_also_returns_no_image(tmp_path):
    """A full disk or a path that is a file, not a directory -- still not the step's problem."""
    blocked = tmp_path / "in-the-way"
    blocked.write_text("not a directory")

    take = shot.step_capture(0x1234, blocked, capture=lambda handle: a_screenshot())
    assert take(0) is None


def test_an_unexpected_error_in_the_capture_is_caught_too(tmp_path):
    """`except Exception`, on purpose: a COM error from a dying provider is not CaptureFailed."""

    def capture(handle):
        raise OSError("win32 said no")

    assert shot.step_capture(0x1234, tmp_path, capture=capture)(0) is None


def test_each_step_gets_its_own_file(tmp_path):
    take = shot.step_capture(0x1234, tmp_path, capture=lambda handle: a_screenshot())
    for index in range(3):
        take(index)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "step-0000.png",
        "step-0001.png",
        "step-0002.png",
    ]


# --- where a run's images go ---------------------------------------------------------------


def test_a_run_id_keys_the_directory_so_one_run_is_one_folder(tmp_path):
    """#44's client sends one `runSteps` per step; without this each step got its own folder."""
    first = shot.new_run_directory(
        tmp_path, run_id="7a3c2f4e-1b2d-4c5e-8f9a-0b1c2d3e4f5a"
    )
    second = shot.new_run_directory(
        tmp_path, run_id="7a3c2f4e-1b2d-4c5e-8f9a-0b1c2d3e4f5a"
    )
    assert first == second == tmp_path / "run-7a3c2f4e-1b2d-4c5e-8f9a-0b1c2d3e4f5a"


def test_two_runs_do_not_share_a_directory(tmp_path):
    assert shot.new_run_directory(tmp_path, run_id="run-a") != shot.new_run_directory(
        tmp_path, run_id="run-b"
    )


def test_without_a_run_id_every_call_gets_its_own_directory(tmp_path):
    from datetime import datetime

    early = shot.new_run_directory(
        tmp_path, moment=datetime(2026, 11, 15, 14, 3, 11, 4812)
    )
    late = shot.new_run_directory(tmp_path, moment=datetime(2026, 11, 15, 14, 9, 0, 1))
    assert early != late
    assert early.name < late.name, "timestamped names sort by when the run started"


@pytest.mark.parametrize(
    "run_id",
    ["../../etc", "..", "a/b", r"C:\windows", "", "x" * 65, ".hidden", "a b"],
)
def test_a_run_id_that_cannot_be_a_directory_name_falls_back(tmp_path, run_id):
    """`runId` crosses a process boundary, so it is a name to check, not a name to trust."""
    directory = shot.new_run_directory(tmp_path, run_id=run_id)
    assert directory.parent == tmp_path, f"{run_id!r} escaped to {directory}"
    assert directory.name.startswith("run-20")


def test_the_fallback_is_announced_rather_than_silent(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        shot.new_run_directory(tmp_path, run_id="../escape")
    assert "cannot name a directory" in caplog.text
