"""
Builds the unicorn's texture atlas: shelf-packs every cube face into one
image, paints the base colors, then paints the facial details (eyes, nostrils,
mouth) on top.

Imported by both tools/generate_addon.py (writes the PNG the addon ships) and
tools/render_preview.py (samples it for the README render), so the preview
shows the same texture the game does.

Side effect on import: populates cube["uv"] on the shared BONES structures.
"""

import math

from unicorn_model import (
    BONE_BY_NAME,
    FACE_ORDER,
    FACE_SHADE,
    MUZZLE,
    face_size,
    iter_cubes,
    shade,
)

TEXTURE_W = 256
PAD = 2  # >=2 so every face gets a private 1px bleed ring (no mipmap color bleed)

EYE_DARK = (28, 26, 38, 255)
EYE_GLINT = (255, 255, 255, 255)
NOSTRIL = (150, 96, 104, 255)
MOUTH = (150, 96, 104, 255)

# ---------------------------------------------------------------------------
# Shelf-pack every cube face into the atlas
# ---------------------------------------------------------------------------

_cursor_x, _cursor_y, _row_h = 0, 0, 0
_allocations = []

for _bone, _cube in iter_cubes():
    _cube["uv"] = {}
    _face_colors = _cube.get("face_colors", {})
    for _face in FACE_ORDER:
        _w, _h = face_size(_cube["size"], _face)
        _w, _h = int(math.ceil(_w)), int(math.ceil(_h))
        if _cursor_x + _w > TEXTURE_W:
            _cursor_x = 0
            _cursor_y += _row_h + PAD
            _row_h = 0
        _u, _v = _cursor_x, _cursor_y
        _cube["uv"][_face] = {"uv": [_u, _v], "uv_size": [_w, _h]}
        _allocations.append((
            (_u, _v, _w, _h),
            shade(_face_colors.get(_face, _cube["color"]), FACE_SHADE[_face]),
        ))
        _cursor_x += _w + PAD
        _row_h = max(_row_h, _h)

used_height = _cursor_y + _row_h
TEXTURE_H = 1
while TEXTURE_H < used_height:
    TEXTURE_H *= 2

for (_u, _v, _w, _h), _ in _allocations:
    assert _u + _w <= TEXTURE_W and _v + _h <= TEXTURE_H, "UV rect out of atlas bounds"

# ---------------------------------------------------------------------------
# Paint: bleed ring first, then the exact rects on top
# ---------------------------------------------------------------------------

pixels = [[(0, 0, 0, 0)] * TEXTURE_W for _ in range(TEXTURE_H)]

for _expand in (1, 0):
    for (_u, _v, _w, _h), _color in _allocations:
        for _yy in range(max(0, _v - _expand), min(TEXTURE_H, _v + _h + _expand)):
            for _xx in range(max(0, _u - _expand), min(TEXTURE_W, _u + _w + _expand)):
                pixels[_yy][_xx] = _color


# ---------------------------------------------------------------------------
# Facial details, painted after the base fill so they aren't bled outward
# ---------------------------------------------------------------------------

def face_rect(cube, face):
    """(u, v, w, h) of a cube face's slot in the atlas."""
    u, v = cube["uv"][face]["uv"]
    w, h = cube["uv"][face]["uv_size"]
    return u, v, w, h


def _put(x, y, color):
    if 0 <= x < TEXTURE_W and 0 <= y < TEXTURE_H:
        pixels[y][x] = color


def _rect(u, v, w, h, color):
    for yy in range(v, v + h):
        for xx in range(u, u + w):
            _put(xx, yy, color)


_head = BONE_BY_NAME["head"]["cubes"][0]

# --- Front of the face (north): muzzle patch, nostrils, mouth ---
#
# The face is 8 wide x 9 tall. Texture V increases downward while model Y
# increases upward, so row 0 is the forehead and row 8 is the chin -- that
# vertical mapping is what puts the mouth below the nostrils rather than on
# the forehead.
#
# Every detail here is left-right symmetric on purpose: Bedrock's horizontal
# UV winding for a given face isn't something this build can verify without
# launching the game, and symmetric art looks identical either way.
_fu, _fv, _fw, _fh = face_rect(_head, "north")
_muzzle = shade(MUZZLE, FACE_SHADE["north"])

_rect(_fu, _fv + 3, _fw, _fh - 3, _muzzle)          # muzzle covers the lower face
_rect(_fu + 2, _fv + 4, 1, 2, NOSTRIL)              # nostrils (cols 2 and 5 mirror)
_rect(_fu + 5, _fv + 4, 1, 2, NOSTRIL)
_rect(_fu + 2, _fv + 7, 4, 1, MOUTH)                # mouth, centred

# --- Eyes on both side faces (east/west) ---
# Horizontally centred for the same winding-agnostic reason as above. Kept at
# 3x3 rather than something daintier: the side of the head is steeply
# foreshortened from most viewing angles, and a 2px eye disintegrates into
# stair-stepping instead of reading as an eye.
for _face in ("east", "west"):
    _eu, _ev, _ew, _eh = face_rect(_head, _face)
    _ex = _eu + (_ew - 3) // 2
    _ey = _ev + 2
    _rect(_ex, _ey, 3, 3, EYE_DARK)
    _put(_ex, _ey, EYE_GLINT)  # catchlight in one corner
