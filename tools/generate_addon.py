import json
import math
import os

from png_writer import write_png
from unicorn_model import (
    BONES,
    COLLISION_W,
    COLLISION_H,
    SEAT_Y,
    SPAN_X,
    SPAN_Y,
    SPAN_Z,
    model_max,
    model_min,
)
from unicorn_texture import TEXTURE_H, TEXTURE_W, pixels, used_height

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

# Bedrock requires the RP header version, the BP header version, and the BP's
# dependency-on-RP version to agree, or the packs can silently fail to load
# together. Driving all three from one constant makes that impossible to get
# wrong.
PACK_VERSION = [1, 0, 1]


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


print(f"model world AABB: x[{model_min[0]:.2f},{model_max[0]:.2f}] "
      f"y[{model_min[1]:.2f},{model_max[1]:.2f}] z[{model_min[2]:.2f},{model_max[2]:.2f}]")

# visible_bounds must enclose the rotated model or it culls at screen edges.
vb_width = math.ceil(max(SPAN_X, SPAN_Z) / 16.0 * 2) / 2 + 0.5
vb_height = math.ceil(SPAN_Y / 16.0 * 2) / 2 + 0.5
vb_offset_y = round((model_min[1] + model_max[1]) / 2 / 16.0, 2)

# The atlas (packing, base colors, and the painted face) lives in
# unicorn_texture.py so tools/render_preview.py can sample the very same
# pixels. Importing it also populates cube["uv"] used by the geometry below.
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
        "version": PACK_VERSION,
        "min_engine_version": [1, 21, 80],
        "pack_scope": "world",
    },
    "modules": [{"type": "resources", "uuid": RP_MODULE_UUID, "version": PACK_VERSION}],
})

write_json(os.path.join(BP_DIR, "manifest.json"), {
    "format_version": 2,
    "header": {
        "name": "Ride a Unicorn BP",
        "description": "Behavior pack for the Ride a Unicorn addon",
        "uuid": BP_HEADER_UUID,
        "version": PACK_VERSION,
        "min_engine_version": [1, 21, 80],
    },
    "modules": [{"type": "data", "uuid": BP_MODULE_UUID, "version": PACK_VERSION}],
    "dependencies": [{"uuid": RP_HEADER_UUID, "version": PACK_VERSION}],
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
