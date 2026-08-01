"""
Single source of truth for the unicorn's 3D model: bones, cubes, colors, and
the geometry math to place them in world space.

Both tools/generate_addon.py (emits the .geo.json + texture) and
tools/render_preview.py (renders a README screenshot) import this module, so
the addon and its preview image can never drift apart.
"""

import math

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

WHITE = (255, 255, 255, 255)
MUZZLE = (235, 205, 210, 255)
HOOF = (60, 45, 40, 255)
IVORY = (240, 230, 200, 255)
GOLD = (212, 175, 55, 255)
PINK = (255, 105, 180, 255)
PURPLE = (170, 90, 220, 255)
BLUE = (110, 180, 255, 255)
TEAL = (100, 220, 190, 255)
GREEN = (150, 230, 130, 255)

# ---------------------------------------------------------------------------
# Model
#
# Bedrock bone rotation about X is INVERTED relative to standard math: a
# positive X rotation tips the front of a bone down/forward and swings a
# downward-hanging bone backward (+Z). Verified against vanilla horse_v3:
# Neck rotation [30,0,0] carries the head forward+down, Tail [25,0,0] sweeps
# the tail down+back. All rotations below assume that convention.
#
# The entity faces -Z (head at negative Z, tail at positive Z), matching vanilla.
# ---------------------------------------------------------------------------

NECK_ROT_X = 20   # tips head forward/up-and-out
TAIL_ROT_X = 25   # matches vanilla horse; sweeps tail down and back

BONES = [
    {
        "name": "body", "parent": None, "pivot": [0, 22, 2],
        "cubes": [
            {"origin": [-7, 16, -10], "size": [14, 12, 24], "color": WHITE},
        ],
    },
    {
        "name": "leg_front_right", "parent": "body", "pivot": [-5, 16, -7],
        "cubes": [
            {"origin": [-6.5, 4, -8.5], "size": [3, 12, 3], "color": WHITE},
            {"origin": [-6.5, 0, -8.5], "size": [3, 4, 3], "color": HOOF},
        ],
    },
    {
        "name": "leg_front_left", "parent": "body", "pivot": [5, 16, -7],
        "cubes": [
            {"origin": [3.5, 4, -8.5], "size": [3, 12, 3], "color": WHITE},
            {"origin": [3.5, 0, -8.5], "size": [3, 4, 3], "color": HOOF},
        ],
    },
    {
        "name": "leg_back_right", "parent": "body", "pivot": [-5, 16, 11],
        "cubes": [
            {"origin": [-6.5, 4, 9.5], "size": [3, 12, 3], "color": WHITE},
            {"origin": [-6.5, 0, 9.5], "size": [3, 4, 3], "color": HOOF},
        ],
    },
    {
        "name": "leg_back_left", "parent": "body", "pivot": [5, 16, 11],
        "cubes": [
            {"origin": [3.5, 4, 9.5], "size": [3, 12, 3], "color": WHITE},
            {"origin": [3.5, 0, 9.5], "size": [3, 4, 3], "color": HOOF},
        ],
    },
    {
        "name": "neck", "parent": "body", "pivot": [0, 28, -8], "rotation": [NECK_ROT_X, 0, 0],
        "cubes": [
            {"origin": [-4, 28, -11], "size": [8, 10, 6], "color": WHITE},
        ],
    },
    {
        "name": "head", "parent": "neck", "pivot": [0, 38, -8],
        "cubes": [
            {
                "origin": [-4, 34, -18], "size": [8, 9, 10], "color": WHITE,
                "face_colors": {"north": MUZZLE},
            },
        ],
    },
    {
        "name": "ears", "parent": "head", "pivot": [0, 43, -10],
        "cubes": [
            {"origin": [-3.5, 43, -11], "size": [2, 3, 2], "color": WHITE},
            {"origin": [1.5, 43, -11], "size": [2, 3, 2], "color": WHITE},
        ],
    },
    {
        # rotation 0: inherits the neck's forward tilt so the horn angles
        # forward off the forehead instead of standing vertical.
        "name": "horn", "parent": "head", "pivot": [0, 43, -15],
        "cubes": [
            {"origin": [-1.5, 43, -16.5], "size": [3, 6, 3], "color": IVORY},
            {"origin": [-0.75, 49, -15.75], "size": [1.5, 4, 1.5], "color": GOLD},
        ],
    },
    {
        # Crest hugging the neck. Cubes stay near the neck's back edge (z ~ -4)
        # so the neck rotation can't lift them off the body -- the trailing
        # section lives on `mane_back` (parented to body) instead.
        "name": "mane", "parent": "neck", "pivot": [0, 33, -8],
        "cubes": [
            {"origin": [-1, 38, -10], "size": [2, 6, 5], "color": PINK},
            {"origin": [-1, 32, -8], "size": [2, 7, 4], "color": PURPLE},
            {"origin": [-1, 26, -7], "size": [2, 8, 3], "color": BLUE},
        ],
    },
    {
        # Parented to body (unrotated) so it sits flush on the back. Slightly
        # narrower than `mane` so overlapping side faces can't z-fight.
        "name": "mane_back", "parent": "body", "pivot": [0, 28, 0],
        "cubes": [
            {"origin": [-0.95, 27, -4], "size": [1.9, 3, 7], "color": TEAL},
            {"origin": [-0.95, 27, 3], "size": [1.9, 2, 6], "color": GREEN},
        ],
    },
    {
        "name": "tail", "parent": "body", "pivot": [0, 26, 14], "rotation": [TAIL_ROT_X, 0, 0],
        "cubes": [
            {"origin": [-1, 16, 13], "size": [2, 10, 2], "color": BLUE},
            {"origin": [-1, 8, 13], "size": [2, 9, 2], "color": PURPLE},
            {"origin": [-1, 2, 13], "size": [2, 7, 2], "color": PINK},
        ],
    },
]

BONE_BY_NAME = {b["name"]: b for b in BONES}

FACE_ORDER = ["north", "south", "east", "west", "up", "down"]
FACE_SHADE = {"up": 1.08, "down": 0.8, "north": 1.0, "south": 0.92, "east": 0.96, "west": 0.96}


def face_size(size, face):
    sx, sy, sz = size
    if face in ("north", "south"):
        return sx, sy
    if face in ("east", "west"):
        return sz, sy
    return sx, sz


def shade(color, factor):
    r, g, b, a = color
    f = lambda v: max(0, min(255, int(v * factor)))
    return (f(r), f(g), f(b), a)


# ---------------------------------------------------------------------------
# Bone-chain geometry math -- transforms a point/cube from bone-local space to
# world space by walking up the parent chain applying each bone's rotation
# about its own pivot.
# ---------------------------------------------------------------------------

def rotate_x_mc(y, z, deg):
    """Bedrock X-axis bone rotation (inverted vs standard math)."""
    t = math.radians(-deg)
    return y * math.cos(t) - z * math.sin(t), y * math.sin(t) + z * math.cos(t)


def to_world(point, bone_name):
    """Walk up the bone chain applying each bone's rotation about its pivot."""
    x, y, z = point
    name = bone_name
    while name:
        bone = BONE_BY_NAME[name]
        rot = bone.get("rotation")
        if rot and rot[0]:
            px, py, pz = bone["pivot"]
            ry, rz = rotate_x_mc(y - py, z - pz, rot[0])
            y, z = py + ry, pz + rz
        name = bone.get("parent")
    return x, y, z


def cube_world_corners(cube, bone_name):
    """All 8 corners of a cube transformed to world space."""
    ox, oy, oz = cube["origin"]
    sx, sy, sz = cube["size"]
    return [
        to_world((ox + dx * sx, oy + dy * sy, oz + dz * sz), bone_name)
        for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)
    ]


def cube_world_aabb(cube, bone_name):
    xs, ys, zs = zip(*cube_world_corners(cube, bone_name))
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def iter_cubes():
    """Yields (bone, cube) for every cube in the model."""
    for bone in BONES:
        for cube in bone["cubes"]:
            yield bone, cube


# ---------------------------------------------------------------------------
# Verify the model geometrically at import time. Computes each cube's
# world-space AABB through its bone chain so bugs like a mane floating above
# the back or a tail tucked under the belly are caught here rather than
# in-game -- both generate_addon.py and render_preview.py get this for free.
# ---------------------------------------------------------------------------

model_min = [1e9, 1e9, 1e9]
model_max = [-1e9, -1e9, -1e9]
_cube_bounds = []
for _bone, _cube in iter_cubes():
    _lo, _hi = cube_world_aabb(_cube, _bone["name"])
    _cube_bounds.append((_bone["name"], _lo, _hi))
    for _i in range(3):
        model_min[_i] = min(model_min[_i], _lo[_i])
        model_max[_i] = max(model_max[_i], _hi[_i])

BODY_TOP = 28.0  # body cube spans y 16..28, unrotated


def _aabb_overlap(a, b, tol=1.0):
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[i] <= bhi[i] + tol and blo[i] <= ahi[i] + tol for i in range(3))


# Mane pieces must actually touch the neck or the body -- the neck's rotation
# lifts anything trailing behind it, which previously left the rear of the mane
# floating in mid-air above the back.
_anchors = [
    cube_world_aabb(BONE_BY_NAME["neck"]["cubes"][0], "neck"),
    cube_world_aabb(BONE_BY_NAME["body"]["cubes"][0], "body"),
]
for _bone in BONES:
    if _bone["name"] not in ("mane", "mane_back"):
        continue
    for _cube in _bone["cubes"]:
        _box = cube_world_aabb(_cube, _bone["name"])
        assert any(_aabb_overlap(_box, _a) for _a in _anchors), (
            f"{_bone['name']} cube at {_cube['origin']} floats detached "
            f"(world y {_box[0][1]:.2f}..{_box[1][1]:.2f}, z {_box[0][2]:.2f}..{_box[1][2]:.2f})"
        )

# Feet must reach the ground plane, and nothing may sink below it.
assert abs(model_min[1]) < 1e-6, f"model does not sit on y=0 (min y={model_min[1]:.2f})"

# Tail must sweep BACKWARD (+Z), not tuck forward under the belly.
_tail_lo, _tail_hi = cube_world_aabb(BONES[-1]["cubes"][-1], "tail")
assert _tail_hi[2] > 14.0, f"tail tip did not sweep behind the body (max z={_tail_hi[2]:.2f})"

# visible_bounds / camera framing must enclose the rotated model.
SPAN_X = model_max[0] - model_min[0]
SPAN_Y = model_max[1] - model_min[1]
SPAN_Z = model_max[2] - model_min[2]

# The rider sits the same distance below the back as a vanilla horse rider
# (horse back top 21u = 1.3125b, seat 1.1b -> 0.2125b below).
SEAT_Y = round(BODY_TOP / 16.0 - 0.2125, 3)
COLLISION_W = round((14 + 10) / 16.0, 2)   # body length 24u -> 1.5b (vanilla scales width to length)
COLLISION_H = 1.9                           # above the 1.75b back, still <=2 so pathing needs only 2 blocks
