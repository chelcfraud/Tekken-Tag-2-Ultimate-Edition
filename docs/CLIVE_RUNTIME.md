# Clive runtime support

Clive remains experimental. The changes below implement full attack geometry,
Gigaflare starters, Zantetsuken charge and enhanced continuations, a compact
HUD, Practice level selection, and a level-five charged guard break. They also
restore airborne strings, hit reactions and counter-hit pickup support. They
do not complete Eikon effects or establish that every move behaves
correctly. [Clive import status](CLIVE_IMPORT.md) separates automated checks
from gameplay confirmations and lists the remaining work.

## Change inventory

| Component | Change and purpose |
| --- | --- |
| `tekken8/hitboxes.py` | Export every active source shape, retaining individual windows, radius, height and endpoint offsets, including zero-radius sword reach. Calibrate body and combat-grip frames, preserve virtual midpoints and ground-relative endpoints, and copy shapes to Tag Assault twins. Apply Clive's explicit first-`f+2` contact margin only to rows sharing that animation. |
| `convert/moveset.py` | Keep collision-twin ownership alongside upstream Tag Assault finish-hit and string generation. Preserve character-selected reaction states before inferred remapping. Enable Clive's source gauge mappings and mechanics adapter. |
| `convert/move_overrides.py`, `convert/clive.py` | Restore grounded victim reactions, airborne input/contact latches and the counter-hit pickup capsule. Replace this string's Heat gate with level 5; preserve charge/release behavior and create an isolated guard-break recovery state. |
| `importer.py` | Build full geometry with the converted moves, bind it to the final serialized moveset after retargeting, extract local numeral masks, and identify the runtime sidecar separately from legacy-summary audit differences. |
| `characters/clive.py` | Opt into full hitboxes, Zantetsuken, airborne strings, pickup support and charged guard breaks. Preserve selected shared reactions and the first-`f+2` contact adjustment. Clive's own revision is 12. Keep the experimental warning. |
| `title/imported_hitboxes.h` | Parse and validate sidecars, transform endpoints, compose local and parent frames, and build swept or vertical segments. |
| `title/imported_hurtbox.h` | Decode the source auxiliary hurt capsule and track its owning reaction, dimensions, enable/disable state and Trans-local offset. |
| `title/roster.cpp` | Load sidecars; evaluate attack segments and auxiliary hurt capsules through native collision; manage independent actor gauges and held charges; connect Practice selection and confirmed guard-break costs to the HUD. |
| `title/clive_state.h` | Clamp charge to 0-200, support levels 1-5, snapshot attack-entry charge, track held/released inputs and confirmed victims, spend one level per guard break, and recognize private dynamic requirements. |
| `title/clive_practice_menu.h` | Extend the native BX01 Practice menu with an English level selector and chooser. Preserve native Xtal handlers while renaming their serialized constants and updating binary offsets. |
| `tekken8/clive_hud.py` | Extract only the original numeral alpha masks from the player's Tekken 8 installation. |
| `title/clive_hud.h` | Validate numeral masks, publish independent actor snapshots, and rasterize the existing compact numeral with a thin next-level progress bar. |
| `gpu/vulkan/clive_hud.cpp`, `renderer.cpp`, `renderer.h` | Alpha-blend the HUD onto the TV scan image with native Vulkan shaders, upload buffers and cached pipelines. Preserve transparency, support RGBA/BGRA scan images and restore renderer pipeline tracking afterwards. |
| Build files and tests | Register the HUD renderer and meter tests, and add the Windows native cancel-classification regression against the player's generated game. Extend importer and native collision regressions. |
| `.gitignore` | Exclude generated `.hitboxes` and `.zanhud` files alongside existing game-derived pack formats. |

Module paths above are relative to `tools/characters/ttt2char/` or
`runtime/src/`, as appropriate. No extracted game assets, generated packs,
executables, saves, captures, local diagnostic scripts or backups are published.

## Collision behavior

The previous native summary represented at most two points and one active
window. It could erase a sword's local offset when its radius was zero or
omit later shapes in a string. The sidecar keeps up to eight source shapes
per move and their independent inclusive frame windows. The native move's
eligibility window covers their union; the runtime still tests each shape
only during its own window.

The runtime calls the native segment/hurt-capsule path (`039C0508`), with
radius scoped to that test. Guard, damage, reactions and invulnerability stay
in the native caller. Missing geometry entries use the original collision
path. A malformed sidecar or moveset CRC mismatch causes the fighter to be
skipped with a reimport diagnostic.

Weapon transforms retain the native skeleton's previous-frame alignment.
Their local samples are composed with the current parent transform during
collision, including a refresh when posing and collision share a logic-frame
number. The previous sweep endpoint remains fixed for that frame, including
checks against multiple defenders. This addresses lost follow-up reach in
`f+1+2`; the `df+2` fix also preserves its source grounded reaction. Further
gameplay validation of both strings away from walls remains open.

## Special moves and charge

Gigaflare (`uf+1+2`) imports `Thrmv_B2_00` and `Thrmv_B2_01` as Clive's own
starter rows and animations. Their active windows are 12-14 and 15-17,
respectively, matching their continuation checks and paired victim states.

Zantetsuken uses a separate gauge for each actor, including mirrors and tag
partners. Charge is 0-200; levels 1-5 begin at 0, 50, 100, 150 and 200.
The source's signed gains and consumption are retained. Base `1+4` gains
10 on a captured hit or 5 on a captured block; a whiff earns neither.
Attack-entry charge determines the enhanced branch, so the current strike's
gain cannot unlock a higher branch for that same strike.

Both neutral and Phoenix Shift `1+4` prioritize thresholds 200, 150, 100, 50.
Enhanced cancels use private charge predicate `0x7F02`, native grab eligibility
2 and native unguarded hit predicate 46. Their window is 22-23, and the
continuation starts at animation frame 23. Native contact checks run while
the victim still records the attacker. The later captured-contact variable
314 is used for gains only. Calling the complete native evaluator from a
gain property with no opponent previously crashed; that property now reads
the verified latch at actor offset `0x1F8` directly.

Native preparation classifiers `0404F398` and `0404F3D4` must also recognize
the private predicates. Otherwise, their high ids cause cancel option bit 2
to be set and the enhanced branches are skipped before combat evaluation.
The classifiers preserve the original treatment of native ids and properties.
`TTT2_TRACE_CLIVE` reports charge, native contact results and selected routes.

Ultimate uses the distinct 380-frame source animation and consumes 200 charge
at its source-timed frame 266. Local gameplay confirmed the long animation;
the trace also confirmed selection of threshold 200 on contact frame 22,
consumption to zero, and normal attacks afterwards. Lower enhanced routes
retain their source throw damage, victim animations and timed consumption.

## Strings, reactions and pickup corrections

`uf+2` now retains its input and contact latches across all three attack rows,
using native persistent words as Noctis does. The starter clears both words;
the frame-34 finisher requires both buffered input and confirmed contact.
Whiffs cannot qualify, and an interrupted attempt cannot seed the next one.
The converter also restores the targeted victim reactions for `uf+1+2`,
`df+1,1` and `db+1,1`, retaining their separate airborne and bound branches.

Clive preserves `sDm_kawa30`, `sDm_kawa30G`, `sGrd_kakaStA22G` and
`sDm_sjk02tk5` wherever referenced. This covers conditional and unnamed
variants of `f+2` and its strings, avoiding inferred substitutions with
`motOrigin`, airborne reactions or `Fall_sKAM`. The separate `df+2` stagger
correction remains in place.

CH `d+1+2` restores the source victim's auxiliary hurt capsule from frame 45
until its frame-60 disable property. It has a Trans-local offset of
`(0,0,950)` mm, half-height 100 mm and radius 400 mm. The runtime tests it only
after the fourteen ordinary hurt capsules miss, temporarily substituting and
then restoring a native slot. Ownership and disable checks prevent stale
volumes; the capsule follows Trans rather than the falling hips' rotation.
This works when the victim is a native fighter as well as an imported one.

The first `f+2` clip separately opts into a 100 mm minimum shape radius and
an inclusive active window of frames 15-16 instead of frame 15 alone. Rows
sharing that clip, including unnamed variants and tag twins, receive the same
adjustment. It compensates for the measured retargeted blade position; it is
a compatibility change, not the source's authored geometry. Other attacks
retain their dimensions and windows. Full combo replays remain manual checks.

## Practice level selection

Open **Practice → Advanced Settings → Clive Enhanced State**. The label and
chooser are in English, and the available values are **1, 2, 3, 4, 5**.
The row is visible and focusable only when Clive is on the player's Practice
team, including as a tag partner. Without Clive on that team the row is
hidden; an opponent-only Clive does not enable the player's setting.

Selecting a level sets the corresponding actor's gauge to 0, 50, 100, 150 or
200 points and refreshes the HUD. Opening the menu reads the current level.
Confirming the same number can reset partial progress within that level.
The selected value seeds subsequent Practice round resets; normal combat
gains and consumption still operate between resets. New actor setup clears
the previous actor's selection and widget tracking.

The runtime patches the locally loaded native menu resource `0xE23E4D32`
through the archive overlay. It adds a row, five-value selector, description
and chooser while retaining native navigation handlers. No extracted menu
resource is distributed. Invalid layouts produce a diagnostic instead of
silently writing an incompatible menu.

## Level-five charged guard break

The source Heat-only LP branch after `f+2,2` is available at **level 5 (200
points)**. Its input window remains frames 1-25 of the second strike. Holding
the final **1** through the source charge deadline, frame 21 of the finisher
in the inspected dump, enables the charged reaction. Releasing early, even
when followed by another press, retains the normal block reaction.

The source animation, 30/25 charged/tap damage variants and airborne hit
branches are preserved. Only the grounded charged block reaction points to
`Okm_CliveGuardBreak`, a private copy of the shared source guard state.
Its neutral return moves from frame 45 to **47**. With attacker recovery at
60 and active frames 26-27, this gives **+13 on first-frame contact and +14
on late contact**. This admits slower follow-ups than the previous +11/+12
window while keeping i15 launchers outside the guaranteed window. Other
attacks using the shared guard state keep their existing recovery.

Entering that victim state confirms the recorded attacker/victim pair and
sets the attacker's gauge to **150 points (level 4)**. The cost runs once per
charged attack. Whiffs, ordinary hits, early releases and another victim's
state do not pay. The attack retains its confirmed charged classification
after payment, preventing a second active-frame evaluation from changing the
selected reaction. A new attempt clears that confirmation and needs level 5
again. Other Heat branches remain disabled.

| Private id | Purpose |
| --- | --- |
| Requirement `0x7F03` | Completed held charge with the level-five gate; treated as a dynamic predicate by native preparation. |
| Property `0x8F04` | Begin the per-actor charge latch with the source deadline. |
| Property `0x8F05` | Confirm actual guard-break victim entry and pay the level-five-to-four cost once. |
| Properties `0x8F10`–`0x8F13` | Auxiliary hurt-capsule offset, size and clear operations on the victim reaction. |

## Compact HUD

The accepted numeral remains at its existing position below the HP bar,
inset from the portrait. A 24-by-2 pixel bar beneath the 32-pixel numeral
shows progress towards the next level, resetting when the numeral increases.
At level 5, both the numeral and the full bar are gold. Dimensions scale
with the scan image; the transparent raster is 32 by 38 pixels at base scale.

Only the on-field Clive is drawn for each side. Tag partners keep independent
charge, and snapshots expire after 750 ms without combat updates. The renderer
uses atomic snapshots rather than reading simulation-owned maps. Numeral
masks use a mutex-protected shared store. Missing or invalid numeral data
uses fallback digits. The overlay is part of the TV scan image and its captures.

## Local sidecar formats

Both formats use little-endian headers and are generated from owned local
files. They are not checked into Git.

### Attack geometry: `<code>.hitboxes`

| Record | Layout |
| --- | --- |
| Header, 16 bytes | `T8HB`, version `u32=1`, final moveset CRC32 `u32`, move count `u32` |
| Move, 8 bytes | Global move id `u32` (`move_id_hi << 16 \| move_id_lo`), shape count `u32` |
| Shape, 104 bytes | Inclusive first/last frames `2*u32`, radius/height `2*f32`, two 44-byte endpoints |
| Endpoint, 44 bytes | Kind, point/pair A, point B, bone A, bone B (`5*u32`), two local offsets (`6*f32`) |

Endpoint kinds are 0: native point; 1: body point with calibrated offset;
2: combat weapon frame with offset; 3: virtual midpoint; 4: ground-relative
frame; 5: previous-to-current swept endpoint. Kind 5 is allowed only as the
second endpoint. A positive height creates a vertical capsule segment.
The reader validates counts, duplicate move ids, frame ranges, finite bounded
coordinates, nonnegative radius/height, endpoint indices, CRC and exact length.

### Numerals: `clv.zanhud`

The 16-byte header contains `ZHUD`, version `u32=1`, width `u32`, height `u32`.
Five consecutive `width*height` alpha masks follow, for levels 1-5. The importer
extracts the five nonempty cells from `T_UI_HUD_Pow_okm_Num`, downsamples each
to 128 by 128, and writes 81,936 bytes total. The runtime validates dimensions
and exact length. Digit color and the progress bar are generated by the HUD.

## Updating and verifying

Rebuild the runtime and reimport Clive through the launcher to update an older
pack. Current Clive packs report **revision 17**: shared pack revision 5 plus
Clive revision 12. Both updated code and regenerated data are required; an old
pack does not gain the new string routes, guard-break reaction or cost marker
automatically. The Practice menu itself is supplied by the updated runtime.
The local development installation was updated with a backup of its previous
executable and Clive pack. Those machine-specific backups remain ignored.

Run the configured CTest suite with:

```text
ctest --test-dir <build-directory> --output-on-failure
```

With the character importer's Python dependencies available, run:

```text
python -m unittest discover -s tools/characters/tests -p test_tekken8_hitboxes.py
python -m unittest discover -s tools/characters/tests -p test_move_overrides.py
python -m unittest discover -s tools/characters/tests -p test_clive_mechanics.py
python -m unittest discover -s tools/characters/tests -p test_tekken8_convert.py
```

For a focused check that does not launch the game, run:

```text
ctest --test-dir <build-directory> -R "^clive_(state|practice_menu)_test$" --output-on-failure
```

`clive_practice_menu_test` uses synthetic menu data and can additionally check
a privately extracted native Practice resource with
`clive_practice_menu_test <native-practice-resource>`. It verifies five values,
English labels, chooser naming, binary table offsets and idempotent patching.
`clive_state_test` covers the five levels, full holds, early release/re-press,
interruption, confirmed-victim matching, the 200-to-150 cost, duplicate
confirmation and the next attempt's gate. Converter tests check scoped
reaction cloning, +13/+14 recovery calculations, retained damage and normal
reactions, and the private marker on the dedicated victim state.

`weapon_collision_test` exercises native blade/hurt-capsule geometry and can
also validate a generated sidecar against its final moveset:

```text
weapon_collision_test <Tekken.rpx> <fighter.hitboxes> <fighter.moveset>
clive_cancel_test <Tekken.rpx>
```

The Windows CMake configuration registers the native tests against the local
RPX path. `clive_cancel_test` reproduces the disabled-row bug with the original
routines, checks all private predicates, and compares classifications for
native ids 0-1023, properties and an unrelated unknown id. `clive_state_test`
covers charge, reset, consumption, entry snapshots, HUD expiry, transparency
and empty/half/full progress bars. Importer tests cover eight shapes,
independent windows, tag twins, calibrated offsets, retained grounded reactions,
conditional gains, branch priority and both throw starters.

The verified real pack contains 227 attack moves and 683 active shapes.
Gameplay feedback confirms `b+1`, Gigaflare, charge accumulation and Ultimate
Zantetsuken. Automated geometry and data checks cover additional cases;
they do not certify every move, facing, wall or tag interaction.

Earlier publication checks on 2026-10-27: the Windows runtime built successfully and
all 17 CTest tests passed. The Python suite completed 659 tests across 63
modules with no failures and 9 individual skips. The POSIX-only
`test_launcher.py` module was excluded on Windows. Native validation also
loaded the real 227-move sidecar against its final moveset CRC, and generated
pack checks retained both Gigaflare starter windows, all four enhanced routes,
paired victim links, consumption and the distinct Ultimate animation.

The later Practice and guard-break publication checks passed 87 Python tests
across the Clive mechanics, hitbox, move-override, movement, Tekken 8 converter
and tag-system modules, plus both focused CTest tests. The Windows runtime
build was up to date. These checks did not launch the game. Offline checks of
the regenerated revision-17 pack verified
the level-five route, frame-21 hold marker, dedicated frame-47 guard state,
normal/air/tap reaction preservation and matching moveset/sidecar CRC. The
guard-break balance change retained all attack geometry by move name; raw
move ids can shift when the new reaction is inserted. The user's gameplay
feedback established that the earlier break permitted `1,1`; the expanded
window and new cost have automated and data validation, with manual gameplay
verification left to the user. Do not start the game for these checks.

Set `TTT2_TRACE_IMPORTED_HITBOXES=1` for per-shape collision diagnostics or
`TTT2_TRACE_CLIVE=1` for meter and continuation diagnostics before launching
the game. The usual launcher game log receives the output. Both flags are
optional and disabled during normal launches.

## Upstream integration

The work includes Petexy's `codex/armor-king-t8-moves` through `9ee2e52`:
`390eac3` updates Reina bounds, Tag Assault strings and assist control;
`9ee2e52` adds optional native Armor King T8 moves, wall throw and airborne
reactions. The converter retains those finish-hit/string rules alongside
Clive's collision twins. The previously published commits remain represented
when reconciling the rebased branch, preserving remote history for a normal push.
