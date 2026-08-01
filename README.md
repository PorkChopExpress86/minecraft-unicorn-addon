# Ride a Unicorn

A Minecraft Bedrock Edition addon that adds a rideable unicorn: a custom entity with hand-built
geometry, texture, and animations, tameable-free riding (walk up and interact to mount), and a
rare natural spawn.

**[Download the latest `.mcaddon`](https://github.com/PorkChopExpress86/minecraft-unicorn-addon/releases/latest)**
-- double-click it to import into Minecraft. No build step needed to just play it.

![Unicorn preview](assets/preview.png)

*Rendered by `tools/render_preview.py` from the same geometry (`tools/unicorn_model.py`) and the
same texture (`tools/unicorn_texture.py`) that the addon itself ships -- not a hand-picked
screenshot, so it can't show a model or a texture the game won't. In-game lighting differs.*

## Structure

```
UnicornAddon_BP/       Behavior pack -- entity definition, spawn rules
UnicornAddon_RP/       Resource pack -- geometry, texture, animations, render controller
UnicornAddon_TestBP/   Dev-only behavior pack -- automated in-game self-test (see below)
assets/
  preview.png          README screenshot, rendered by tools/render_preview.py
tools/
  unicorn_model.py      Shared source of truth: the unicorn's bones/cubes/colors + geometry math
  unicorn_texture.py    Shared texture atlas: UV packing, base colors, and the painted face
  generate_addon.py     Generates every BP/RP file from the two modules above
  render_preview.py     Renders assets/preview.png from those same two modules
  png_writer.py          Minimal PNG encoder shared by the two generators above
  sync-to-minecraft.ps1     Copies the packs into Minecraft's dev pack folders
  activate-in-world.ps1     Activates the packs inside an existing world save
UnicornAddon.mcaddon    Packaged build (not committed -- see Packaging below)
```

`UnicornAddon_BP` and `UnicornAddon_RP` are generated output. The real source is
`tools/unicorn_model.py` (geometry) plus `tools/unicorn_texture.py` (texture). Both
`tools/generate_addon.py` (the `.geo.json`, texture PNG, and every UV coordinate) and
`tools/render_preview.py` (the README screenshot above) derive from those two modules, so the
model, the shipped addon, and the preview image can't drift out of sync. To change the model,
palette, or facial details, edit those modules and regenerate -- don't hand-edit the JSON/PNG under
`UnicornAddon_BP`/`UnicornAddon_RP` directly.

## Requirements

- Minecraft Bedrock Edition 1.21.80+
- Python 3 (only for regenerating the addon; not needed to just play it)

## Building

```bash
python tools/generate_addon.py
```

Regenerates `UnicornAddon_BP` and `UnicornAddon_RP` in place. The script asserts model geometry
sanity at build time (feet touch the ground, no detached mane pieces, UV rects stay in bounds) and
will fail loudly rather than emit a broken model.

```bash
python tools/render_preview.py
```

Regenerates `assets/preview.png`. Run this too after any model change so the README screenshot
stays in sync.

## Packaging

```powershell
Compress-Archive -Path UnicornAddon_BP, UnicornAddon_RP -DestinationPath UnicornAddon.mcaddon.zip
Rename-Item UnicornAddon.mcaddon.zip UnicornAddon.mcaddon
```

Double-clicking the resulting `.mcaddon` imports both packs into Minecraft.

## Development / testing

`tools/sync-to-minecraft.ps1` copies `UnicornAddon_BP`, `UnicornAddon_RP`, and the dev-only
`UnicornAddon_TestBP` into Minecraft's `development_behavior_packs` / `development_resource_packs`
folders (both the Microsoft Store install and a standalone-launcher install, if present). Re-run
it after every change, then fully exit and re-enter the world.

`tools/activate-in-world.ps1` switches the packs on inside a world save's
`world_behavior_packs.json` / `world_resource_packs.json` (existing entries are merged, not
overwritten) so you don't have to click through the in-game pack menus by hand.

`UnicornAddon_TestBP` is a separate dev-only behavior pack (never packaged into the `.mcaddon`)
that runs an automated self-test on world join:

- Spawns a unicorn on verified clear ground near the player
- Reads back its components via the Script API and asserts health, movement speed, collision box,
  and every `minecraft:rideable` field (seat position, seat count, interact text, allowed rider
  families) against expected values
- Holds the unicorn in place for 10 seconds after spawning (a script-side position lock, not an
  addon feature) so you have time to walk over and look at it before AI wandering kicks in
- Reports PASS/FAIL per check in chat

Re-run on demand with `/scriptevent unicorn:test`. Opt in to an automated mount check (seats the
player via `EntityRideableComponent.addRider`) with `/scriptevent unicorn:ride`.

## Riding

Walk up to a unicorn and interact with it (right-click / equivalent) to mount immediately -- no
taming or saddle required. Sneak to dismount.
