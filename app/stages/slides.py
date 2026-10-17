"""Stage 4: slides. Render each script entry as a 1920x1080 PNG from the fixed template."""

import struct
import zlib

from app.stages.base import StageContext, register

WIDTH, HEIGHT = 1920, 1080


def solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Encode a single-colour RGB PNG with the stdlib only."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    row = b"\x00" + bytes(rgb) * width  # filter byte 0 + pixels
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(row * height, 9))
        + chunk(b"IEND", b"")
    )


@register("slides", "stub")
def slides_stub(ctx: StageContext) -> None:
    """Offline placeholder: a blank, correctly sized frame per slide (no text yet)."""
    script = ctx.read_json("script.json")
    out = ctx.path("slides")
    out.mkdir(exist_ok=True)
    frame = solid_png(WIDTH, HEIGHT, (15, 23, 42))
    for slide in script["slides"]:
        (out / f"{slide['index']:02d}.png").write_bytes(frame)
