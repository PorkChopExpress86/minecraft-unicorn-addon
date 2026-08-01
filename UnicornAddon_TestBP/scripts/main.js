import { world, system } from "@minecraft/server";

// Automated self-test for the Ride a Unicorn addon.
//
//   /scriptevent unicorn:test    re-run the checks (also runs on first spawn)
//   /scriptevent unicorn:ride    opt-in: seat yourself on the test unicorn
//
// The checks are deliberately non-invasive: they spawn a unicorn on verified
// clear ground nearby and read its components, but never move or mount the
// player. Auto-mounting was removed because it seated the player wherever the
// unicorn happened to be -- inside a tree trunk or hillside, that puts the
// camera inside a solid block and blacks out the screen.

const ENTITY_ID = "unicorn:unicorn";
const TEST_TAG = "unicorn_test";

const EXPECT_SEAT_Y = 1.538;
const EXPECT_HEALTH = 24;
const EXPECT_MOVEMENT = 0.28;
const EPSILON = 0.01;

// The unicorn's collision box is 1.9 blocks tall, so it needs two clear
// blocks; ask for three so it never spawns wedged under an overhang.
const HEADROOM = 3;

// Testing-only affordance: keep the freshly spawned unicorn from wandering
// off (random_stroll) while you're still walking over to look at it. This is
// a script-side position lock, not an addon feature -- it never touches the
// shipped entity definition. Idle/walk animations still play normally; only
// net position is held.
const HOLD_STILL_SECONDS = 10;
const HOLD_STILL_INTERVAL_TICKS = 2;

/** Repeatedly teleports `entity` back to `location` for `seconds`, then stops. */
function holdStill(entity, location, seconds) {
  const rotation = entity.getRotation();
  const totalTicks = seconds * 20;
  let elapsed = 0;

  const id = system.runInterval(() => {
    elapsed += HOLD_STILL_INTERVAL_TICKS;
    try {
      entity.teleport(location, { rotation });
    } catch {
      system.clearRun(id); // entity went invalid -- nothing left to hold
      return;
    }
    if (elapsed >= totalTicks) system.clearRun(id);
  }, HOLD_STILL_INTERVAL_TICKS);
}

function clearPreviousTestEntities(dimension) {
  for (const e of dimension.getEntities({ type: ENTITY_ID, tags: [TEST_TAG] })) {
    try {
      e.remove();
    } catch {
      // already gone, or in an unloaded chunk -- nothing to do
    }
  }
}

function blockAt(dimension, x, y, z) {
  try {
    return dimension.getBlock({ x, y, z });
  } catch {
    return undefined; // unloaded chunk
  }
}

/**
 * Finds standable ground near `origin`: a non-air, non-liquid block with
 * HEADROOM air blocks directly above it. Returns a block-centred spawn point.
 */
function findSpawnSpot(dimension, origin) {
  const ring = [
    [3, 0], [-3, 0], [0, 3], [0, -3],
    [3, 3], [-3, -3], [3, -3], [-3, 3],
    [5, 0], [0, 5], [-5, 0], [0, -5],
  ];
  const ox = Math.floor(origin.x);
  const oy = Math.floor(origin.y);
  const oz = Math.floor(origin.z);

  for (const [dx, dz] of ring) {
    const x = ox + dx;
    const z = oz + dz;
    for (let y = oy + 4; y >= oy - 8; y--) {
      const ground = blockAt(dimension, x, y, z);
      if (!ground || ground.isAir || ground.isLiquid) continue;

      let clear = true;
      for (let dy = 1; dy <= HEADROOM; dy++) {
        const above = blockAt(dimension, x, y + dy, z);
        if (!above || !above.isAir) { clear = false; break; }
      }
      if (clear) return { x: x + 0.5, y: y + 1, z: z + 0.5 };
    }
  }
  return undefined;
}

function runSuite(player) {
  const results = [];
  const pass = (name, detail = "") => results.push({ pass: true, name, detail });
  const fail = (name, detail = "") => results.push({ pass: false, name, detail });
  const near = (a, b) => typeof a === "number" && Math.abs(a - b) < EPSILON;

  const dimension = player.dimension;
  clearPreviousTestEntities(dimension);

  const spot = findSpawnSpot(dimension, player.location);
  if (!spot) {
    fail("found clear ground to spawn on", "no open surface within 5 blocks - move somewhere more open");
    return { results, unicorn: undefined };
  }
  pass("found clear ground to spawn on", `${spot.x}, ${spot.y}, ${spot.z}`);

  let unicorn;
  try {
    unicorn = dimension.spawnEntity(ENTITY_ID, spot);
  } catch (e) {
    fail("spawn entity", `${e} - is "Ride a Unicorn BP" active?`);
    return { results, unicorn: undefined };
  }
  if (!unicorn) {
    fail("spawn entity", "spawnEntity returned nothing");
    return { results, unicorn: undefined };
  }
  unicorn.addTag(TEST_TAG);
  pass("spawn entity");
  holdStill(unicorn, spot, HOLD_STILL_SECONDS);

  unicorn.typeId === ENTITY_ID
    ? pass("typeId", unicorn.typeId)
    : fail("typeId", `${unicorn.typeId} != ${ENTITY_ID}`);

  const health = unicorn.getComponent("minecraft:health");
  if (!health) fail("health component", "missing");
  else if (near(health.effectiveMax, EXPECT_HEALTH)) pass("health max", `${health.effectiveMax}`);
  else fail("health max", `${health.effectiveMax} != ${EXPECT_HEALTH}`);

  const movement = unicorn.getComponent("minecraft:movement");
  if (!movement) fail("movement component", "missing");
  else if (near(movement.currentValue, EXPECT_MOVEMENT)) pass("movement speed", `${movement.currentValue}`);
  else fail("movement speed", `${movement.currentValue} != ${EXPECT_MOVEMENT}`);

  const rideable = unicorn.getComponent("minecraft:rideable");
  if (!rideable) {
    fail("rideable component", "missing - the unicorn cannot be ridden at all");
    return { results, unicorn };
  }
  pass("rideable component");

  rideable.seatCount === 1
    ? pass("seat count", "1")
    : fail("seat count", `${rideable.seatCount} != 1`);

  rideable.crouchingSkipInteract === true
    ? pass("sneak skips mounting")
    : fail("sneak skips mounting", `${rideable.crouchingSkipInteract}`);

  rideable.interactText
    ? pass("ride prompt", rideable.interactText)
    : fail("ride prompt", "empty - no on-screen prompt for touch controls");

  const families = rideable.getFamilyTypes();
  families.includes("player")
    ? pass("players allowed as riders")
    : fail("players allowed as riders", families.join(", ") || "none");

  const seats = rideable.getSeats();
  if (!seats.length) {
    fail("seat defined", "getSeats() returned empty");
  } else {
    const y = seats[0].position.y;
    near(y, EXPECT_SEAT_Y)
      ? pass("seat height", y.toFixed(3))
      : fail("seat height", `${y} != ${EXPECT_SEAT_Y}`);
  }

  return { results, unicorn };
}

function report(results) {
  const passed = results.filter((r) => r.pass).length;
  const failed = results.length - passed;

  world.sendMessage(
    failed === 0
      ? `§a=== Unicorn self-test: all ${passed} checks passed ===`
      : `§c=== Unicorn self-test: ${failed} FAILED, ${passed} passed ===`
  );
  console.log(`Unicorn self-test: ${passed} passed, ${failed} failed`);

  for (const r of results) {
    const detail = r.detail ? ` §7(${r.detail})` : "";
    world.sendMessage(`${r.pass ? "§a  PASS" : "§c  FAIL"} §f${r.name}${detail}`);
    console.log(`  ${r.pass ? "PASS" : "FAIL"} ${r.name}${r.detail ? ` (${r.detail})` : ""}`);
  }

  return failed;
}

let running = false;

function execute(player) {
  if (running) return;
  running = true;
  try {
    const { results, unicorn } = runSuite(player);
    report(results);
    if (unicorn) {
      const l = unicorn.location;
      world.sendMessage(
        `§7A unicorn is waiting at §f${Math.round(l.x)}, ${Math.round(l.y)}, ${Math.round(l.z)}§7 - right-click it to ride.`
      );
      world.sendMessage(`§7Holding it in place for ${HOLD_STILL_SECONDS}s so you can walk over and look it over.`);
    }
    world.sendMessage("§7Re-run: §f/scriptevent unicorn:test§7   Mount me: §f/scriptevent unicorn:ride");
  } catch (e) {
    world.sendMessage(`§cSelf-test crashed: ${e}`);
    console.error(`Self-test crashed: ${e}`);
  } finally {
    running = false;
  }
}

/** Opt-in mount check -- only ever runs when explicitly asked for. */
function mountPlayer(player) {
  const found = player.dimension.getEntities({ type: ENTITY_ID, tags: [TEST_TAG] })[0];
  if (!found) {
    world.sendMessage("§cNo test unicorn nearby. Run §f/scriptevent unicorn:test§c first.");
    return;
  }
  const rideable = found.getComponent("minecraft:rideable");
  if (!rideable) {
    world.sendMessage("§cThat unicorn has no rideable component.");
    return;
  }
  try {
    const added = rideable.addRider(player);
    const mounted = rideable.getRiders().some((e) => e.id === player.id);
    world.sendMessage(
      added && mounted
        ? "§aPASS §fplayer mounted §7(sneak to dismount)"
        : `§cFAIL §fplayer mounted §7(addRider=${added})`
    );
  } catch (e) {
    world.sendMessage(`§cFAIL §fplayer mounted §7(${e})`);
  }
}

// world APIs are unavailable at import time in @minecraft/server 2.x, so
// everything hangs off events.
world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  // Let the surrounding chunks finish loading before probing for ground.
  system.runTimeout(() => execute(ev.player), 100);
});

system.afterEvents.scriptEventReceive.subscribe((ev) => {
  const player = ev.sourceEntity ?? world.getAllPlayers()[0];
  if (!player) return;
  if (ev.id === "unicorn:test") system.run(() => execute(player));
  else if (ev.id === "unicorn:ride") system.run(() => mountPlayer(player));
});
