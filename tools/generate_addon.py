import json
import math
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# Constants -- single source of truth for every identifier used across files
# ---------------------------------------------------------------------------

OUT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP_DIR = os.path.join(OUT_ROOT, "UnicornAddon_BP")
RP_DIR = os.path.join(OUT_ROOT, "UnicornAddon_RP")

NAMESPACE = "unicorn"
ENTITY_ID = f"{NAMESPACE}:unicorn"
GEO_ID = f"geometry.{NAMESPACE}.unicorn"
RENDER_CONTROLLER_ID = f"controller.render.{NAMESPACE}"
ANIM_IDLE_ID = f"animation.{NAMESPACE}.idle"
ANIM_WALK_ID = f"animation.{NAMESPACE}.walk"
ANIM_CONTROLLER_ID = f"controller.animation.{NAMESPACE}.move"

RP_HEADER_UUID = "d33ba74a-0711-42d9-b0ea-7f93fec39060"
RP_MODULE_UUID = "dc4bfd57-53a7-4086-9481-71b1dfa76008"
BP_HEADER_UUID = "607de414-3833-44b6-ba45-81457be8303a"
BP_MODULE_UUID = "b049c417-7246-43b7-8654-830293aee219"

TEXTURE_W = 256
PAD = 2  # >=2 so every face gets a private 1px bleed ring (no mipmap color bleed)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


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
# Verify the model geometrically before emitting anything.
# Computes each cube's world-space AABB through its bone chain so bugs like a
# mane floating above the back or a tail tucked under the belly are caught here
# rather than in-game.
# ---------------------------------------------------------------------------

BONE_BY_NAME = {b["name"]: b for b in BONES}


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


def cube_world_aabb(cube, bone_name):
    ox, oy, oz = cube["origin"]
    sx, sy, sz = cube["size"]
    pts = [
        to_world((ox + dx * sx, oy + dy * sy, oz + dz * sz), bone_name)
        for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)
    ]
    xs, ys, zs = zip(*pts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


model_min = [1e9, 1e9, 1e9]
model_max = [-1e9, -1e9, -1e9]
cube_bounds = []
for bone in BONES:
    for cube in bone["cubes"]:
        lo, hi = cube_world_aabb(cube, bone["name"])
        cube_bounds.append((bone["name"], lo, hi))
        for i in range(3):
            model_min[i] = min(model_min[i], lo[i])
            model_max[i] = max(model_max[i], hi[i])

BODY_TOP = 28.0  # body cube spans y 16..28, unrotated


def aabb_overlap(a, b, tol=1.0):
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[i] <= bhi[i] + tol and blo[i] <= ahi[i] + tol for i in range(3))


# Mane pieces must actually touch the neck or the body -- the neck's rotation
# lifts anything trailing behind it, which previously left the rear of the mane
# floating in mid-air above the back.
anchors = [
    cube_world_aabb(BONE_BY_NAME["neck"]["cubes"][0], "neck"),
    cube_world_aabb(BONE_BY_NAME["body"]["cubes"][0], "body"),
]
for bone in BONES:
    if bone["name"] not in ("mane", "mane_back"):
        continue
    for cube in bone["cubes"]:
        box = cube_world_aabb(cube, bone["name"])
        assert any(aabb_overlap(box, a) for a in anchors), (
            f"{bone['name']} cube at {cube['origin']} floats detached "
            f"(world y {box[0][1]:.2f}..{box[1][1]:.2f}, z {box[0][2]:.2f}..{box[1][2]:.2f})"
        )

# Feet must reach the ground plane, and nothing may sink below it.
assert abs(model_min[1]) < 1e-6, f"model does not sit on y=0 (min y={model_min[1]:.2f})"

# Tail must sweep BACKWARD (+Z), not tuck forward under the belly.
tail_lo, tail_hi = cube_world_aabb(BONES[-1]["cubes"][-1], "tail")
assert tail_hi[2] > 14.0, f"tail tip did not sweep behind the body (max z={tail_hi[2]:.2f})"

print(f"model world AABB: x[{model_min[0]:.2f},{model_max[0]:.2f}] "
      f"y[{model_min[1]:.2f},{model_max[1]:.2f}] z[{model_min[2]:.2f},{model_max[2]:.2f}]")

# visible_bounds must enclose the rotated model or it culls at screen edges.
span_x = model_max[0] - model_min[0]
span_y = model_max[1] - model_min[1]
span_z = model_max[2] - model_min[2]
vb_width = math.ceil(max(span_x, span_z) / 16.0 * 2) / 2 + 0.5
vb_height = math.ceil(span_y / 16.0 * 2) / 2 + 0.5
vb_offset_y = round((model_min[1] + model_max[1]) / 2 / 16.0, 2)

# The rider sits the same distance below the back as a vanilla horse rider
# (horse back top 21u = 1.3125b, seat 1.1b -> 0.2125b below).
SEAT_Y = round(BODY_TOP / 16.0 - 0.2125, 3)
COLLISION_W = round((14 + 10) / 16.0, 2)   # body length 24u -> 1.5b (vanilla scales width to length)
COLLISION_H = 1.9                           # above the 1.75b back, still <=2 so pathing needs only 2 blocks

# ---------------------------------------------------------------------------
# Shelf-pack every cube face into the atlas
# ---------------------------------------------------------------------------

cursor_x, cursor_y, row_h = 0, 0, 0
allocations = []

for bone in BONES:
    for cube in bone["cubes"]:
        cube["uv"] = {}
        face_colors = cube.get("face_colors", {})
        for face in FACE_ORDER:
            w, h = face_size(cube["size"], face)
            w, h = int(math.ceil(w)), int(math.ceil(h))
            if cursor_x + w > TEXTURE_W:
                cursor_x = 0
                cursor_y += row_h + PAD
                row_h = 0
            u, v = cursor_x, cursor_y
            cube["uv"][face] = {"uv": [u, v], "uv_size": [w, h]}
            allocations.append(((u, v, w, h), shade(face_colors.get(face, cube["color"]), FACE_SHADE[face])))
            cursor_x += w + PAD
            row_h = max(row_h, h)

used_height = cursor_y + row_h
TEXTURE_H = 1
while TEXTURE_H < used_height:
    TEXTURE_H *= 2

for (u, v, w, h), _ in allocations:
    assert u + w <= TEXTURE_W and v + h <= TEXTURE_H, "UV rect out of atlas bounds"

# ---------------------------------------------------------------------------
# Paint: bleed ring first, then exact rects on top
# ---------------------------------------------------------------------------

pixels = [[(0, 0, 0, 0)] * TEXTURE_W for _ in range(TEXTURE_H)]

for expand in (1, 0):
    for (u, v, w, h), color in allocations:
        for yy in range(max(0, v - expand), min(TEXTURE_H, v + h + expand)):
            for xx in range(max(0, u - expand), min(TEXTURE_W, u + w + expand)):
                pixels[yy][xx] = color

# Eyes: horizontally centered on the head's side faces so the result reads
# correctly regardless of which way Bedrock winds the east/west UV axis.
head_cube = BONE_BY_NAME["head"]["cubes"][0]
for face in ("east", "west"):
    u, v = head_cube["uv"][face]["uv"]
    w, h = head_cube["uv"][face]["uv_size"]
    ex, ey = u + w // 2 - 1, v + h // 3 - 1
    for yy in range(ey, ey + 2):
        for xx in range(ex, ex + 2):
            pixels[yy][xx] = (20, 20, 25, 255)

write_png(os.path.join(RP_DIR, "textures", "entity", "unicorn.png"), TEXTURE_W, TEXTURE_H, pixels)

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

geo_bones = []
for bone in BONES:
    b = {"name": bone["name"], "pivot": bone["pivot"]}
    if bone["parent"]:
        b["parent"] = bone["parent"]
    if bone.get("rotation"):
        b["rotation"] = bone["rotation"]
    b["cubes"] = [{"origin": c["origin"], "size": c["size"], "uv": c["uv"]} for c in bone["cubes"]]
    geo_bones.append(b)

write_json(os.path.join(RP_DIR, "models", "entity", "unicorn.geo.json"), {
    "format_version": "1.16.0",
    "minecraft:geometry": [{
        "description": {
            "identifier": GEO_ID,
            "texture_width": TEXTURE_W,
            "texture_height": TEXTURE_H,
            "visible_bounds_width": vb_width,
            "visible_bounds_height": vb_height,
            "visible_bounds_offset": [0, vb_offset_y, 0],
        },
        "bones": geo_bones,
    }],
})

# ---------------------------------------------------------------------------
# Animations
# ---------------------------------------------------------------------------

write_json(os.path.join(RP_DIR, "animations", "unicorn.animation.json"), {
    "format_version": "1.10.0",
    "animations": {
        ANIM_IDLE_ID: {
            "loop": True,
            "animation_length": 3.0,
            "bones": {
                "head": {"rotation": ["math.sin(q.anim_time * 120) * 5", 0, 0]},
                "tail": {"rotation": [0, "math.sin(q.anim_time * 90) * 10", 0]},
                "ears": {"rotation": ["math.sin(q.anim_time * 150) * 4", 0, 0]},
                "mane": {"rotation": ["math.sin(q.anim_time * 100) * 3", 0, 0]},
            },
        },
        ANIM_WALK_ID: {
            "loop": True,
            "animation_length": 1.0,
            "bones": {
                "leg_front_right": {"rotation": ["math.cos(q.anim_time * 360) * 35", 0, 0]},
                "leg_back_left": {"rotation": ["math.cos(q.anim_time * 360) * 35", 0, 0]},
                "leg_front_left": {"rotation": ["math.cos(q.anim_time * 360 + 180) * 35", 0, 0]},
                "leg_back_right": {"rotation": ["math.cos(q.anim_time * 360 + 180) * 35", 0, 0]},
                "body": {"position": [0, "math.sin(q.anim_time * 720) * 0.8", 0]},
                "head": {"rotation": ["math.sin(q.anim_time * 360) * 4", 0, 0]},
                "tail": {"rotation": [0, "math.sin(q.anim_time * 540) * 14", 0]},
                "mane": {"rotation": ["math.sin(q.anim_time * 360) * 6", 0, 0]},
            },
        },
    },
})

write_json(os.path.join(RP_DIR, "animation_controllers", "unicorn.animation_controllers.json"), {
    "format_version": "1.10.0",
    "animation_controllers": {
        ANIM_CONTROLLER_ID: {
            "initial_state": "idle",
            "states": {
                "idle": {"animations": ["idle"], "transitions": [{"walking": "q.modified_move_speed > 0.1"}]},
                "walking": {"animations": ["walk"], "transitions": [{"idle": "q.modified_move_speed <= 0.1"}]},
            },
        }
    },
})

write_json(os.path.join(RP_DIR, "render_controllers", "unicorn.render_controllers.json"), {
    "format_version": "1.10.0",
    "render_controllers": {
        RENDER_CONTROLLER_ID: {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
        }
    },
})

write_json(os.path.join(RP_DIR, "entity", "unicorn.entity.json"), {
    "format_version": "1.10.0",
    "minecraft:client_entity": {
        "description": {
            "identifier": ENTITY_ID,
            "materials": {"default": "entity"},
            "textures": {"default": "textures/entity/unicorn"},
            "geometry": {"default": GEO_ID},
            "render_controllers": [RENDER_CONTROLLER_ID],
            "animations": {"idle": ANIM_IDLE_ID, "walk": ANIM_WALK_ID, "controller": ANIM_CONTROLLER_ID},
            "scripts": {"animate": ["controller"]},
            "spawn_egg": {"base_color": "#F5F0FF", "overlay_color": "#FFD700"},
        }
    },
})

# ---------------------------------------------------------------------------
# Behaviour pack entity
#
# `seats` uses the object form -- both object and array are documented, but
# every vanilla sample (horse, llama, pig, cow, minecart) uses the object form.
# `variable_max_auto_step` is required: the default auto-step for a rideable
# entity is 0.5625b, so without it the unicorn cannot walk up a single block
# while ridden. Vanilla horse gets full-block stepping from hardcoded horse
# behaviour that a custom entity does not inherit.
# ---------------------------------------------------------------------------

write_json(os.path.join(BP_DIR, "entities", "unicorn.json"), {
    "format_version": "1.21.50",
    "minecraft:entity": {
        "description": {
            "identifier": ENTITY_ID,
            "is_spawnable": True,
            "is_summonable": True,
            "is_experimental": False,
        },
        "component_groups": {},
        "components": {
            "minecraft:type_family": {"family": ["mob", "animal", "unicorn"]},
            "minecraft:collision_box": {"width": COLLISION_W, "height": COLLISION_H},
            "minecraft:health": {"value": 24, "max": 24},
            "minecraft:movement": {"value": 0.28},
            "minecraft:movement.basic": {},
            "minecraft:jump.static": {"jump_power": 0.42},
            "minecraft:can_power_jump": {},
            "minecraft:variable_max_auto_step": {
                "base_value": 1.0625,
                "controlled_value": 1.0625,
                "jump_prevented_value": 0.5625,
            },
            "minecraft:navigation.walk": {
                "can_walk": True,
                "avoid_water": True,
                "avoid_damage_blocks": True,
            },
            "minecraft:physics": {},
            "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
            "minecraft:knockback_resistance": {"value": 0.4},
            "minecraft:rideable": {
                "seat_count": 1,
                "crouching_skip_interact": True,
                "family_types": ["player"],
                "interact_text": "action.interact.ride.horse",
                "seats": {"position": [0, SEAT_Y, -0.1]},
            },
            "minecraft:input_ground_controlled": {},
            "minecraft:behavior.float": {"priority": 0},
            "minecraft:behavior.panic": {"priority": 1, "speed_multiplier": 1.25},
            "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 1.0},
            "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 8.0},
            "minecraft:behavior.random_look_around": {"priority": 8},
        },
        "events": {},
    },
})

write_json(os.path.join(BP_DIR, "spawn_rules", "unicorn.json"), {
    "format_version": "1.17.0",
    "minecraft:spawn_rules": {
        "description": {"identifier": ENTITY_ID, "population_control": "animal"},
        "conditions": [{
            "minecraft:spawns_on_surface": {},
            "minecraft:spawns_on_block_filter": ["minecraft:grass_block"],
            "minecraft:brightness_filter": {"min": 7, "max": 15, "adjust_for_weather": True},
            "minecraft:difficulty_filter": {"min": "peaceful", "max": "hard"},
            "minecraft:weight": {"default": 5},
            "minecraft:herd": {"min_size": 1, "max_size": 2},
            "minecraft:biome_filter": {"test": "has_biome_tag", "operator": "==", "value": "animal"},
        }],
    },
})

# ---------------------------------------------------------------------------
# Manifests + localization
# ---------------------------------------------------------------------------

write_json(os.path.join(RP_DIR, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Ride a Unicorn RP",
        "description": "Resource pack for the Ride a Unicorn addon",
        "uuid": RP_HEADER_UUID,
        "version": [1, 0, 0],
        "min_engine_version": [1, 21, 80],
        "pack_scope": "world",
    },
    "modules": [{"type": "resources", "uuid": RP_MODULE_UUID, "version": [1, 0, 0]}],
})

write_json(os.path.join(BP_DIR, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Ride a Unicorn BP",
        "description": "Behavior pack for the Ride a Unicorn addon",
        "uuid": BP_HEADER_UUID,
        "version": [1, 0, 0],
        "min_engine_version": [1, 21, 80],
    },
    "modules": [{"type": "data", "uuid": BP_MODULE_UUID, "version": [1, 0, 0]}],
    "dependencies": [{"uuid": RP_HEADER_UUID, "version": [1, 0, 0]}],
})

for d, nm in ((BP_DIR, "BP"), (RP_DIR, "RP")):
    kind = "Behavior" if nm == "BP" else "Resource"
    write_text(os.path.join(d, "texts", "en_US.lang"),
               f"pack.name=Ride a Unicorn {nm}\n"
               f"pack.description={kind} pack for the Ride a Unicorn addon\n"
               f"entity.{ENTITY_ID}.name=Unicorn\n")
    write_text(os.path.join(d, "texts", "languages.json"), json.dumps(["en_US"]) + "\n")

print(f"texture {TEXTURE_W}x{TEXTURE_H} (packed {used_height}px)")
print(f"visible_bounds w={vb_width} h={vb_height} offset_y={vb_offset_y}")
print(f"collision {COLLISION_W}x{COLLISION_H}, seat_y={SEAT_Y}")
print("all geometry assertions passed")
