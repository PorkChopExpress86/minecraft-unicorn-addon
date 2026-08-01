"""Minimal PNG writer (no PIL dependency) -- RGBA, uncompressed-filter scanlines."""

import struct
import zlib
import os


def write_png(path, width, height, pixels):
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (none)
        for x in range(width):
            r, g, b, a = pixels[y][x]
            raw.extend((r, g, b, a))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
