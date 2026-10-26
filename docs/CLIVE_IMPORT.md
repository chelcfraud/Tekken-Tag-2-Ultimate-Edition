# Clive import status

**Experimental: Clive does not work properly. Character and sword hitboxes,
special moves and Eikon effects are incomplete. This is an unfinished prototype,
not a fully working character.** No game assets are
distributed by this implementation; the importer reads the player's local games.

## Existing import paths

Noctis imports his Tekken 7 model, animations and moveset. His weapons use extra
skeleton bones, animation channel pairs after the 23 body channels, and four
held-item collision points (native locations 70–73). Summon properties control
which weapon is drawn. The runtime deliberately aligns these points with the
native collision skeleton's previous frame.

Reina reads Tekken 8's cooked model, materials, skeleton and PANM animations.
Her body animation is retargeted onto the generated Tag 2 skeleton. Her moveset
uses mappings inferred from the native fighters and other locally extracted
Tekken 8 movesets. Generic states retain Tag 2's movement and tag rules.

Clive needs both paths: the Tekken 8 reader and retargeter, plus independent
weapon posing and collision points. Applying Reina's body-only path would bind
the sword to an ordinary body joint and lose its independent transforms.

## Implemented

- Local Clive definition: Tekken 8 ID 36, source code `okm`, pack code `clv`, Lars
  skeleton donor. The default costume's weapon mesh is imported separately.
- Required native Clive moveset extraction; no silent Lars moveset fallback.
- Native `MaterialOverrideNanite` serialization required by his materials.
- Source-neutral weapon model loading and calibrated Tekken 8 weapon transforms.
- Translation, rotation and animated scale channels, including inherited scales
  that move a blade tip. Scale channels use separate extra pairs; existing
  Tekken 7 weapon manifests retain their original format.
- Native weapon posing reads the scale channels. Retargeted weapon chains bypass
  the legacy safeguard against unrelated Tekken 7 item animations several metres
  away from their parent.
- Experimental labeling and a `conversion-report.json` in Clive's generated
  pack. The report retains all eight source shapes, windows, radii and offsets
  for every converted source move, identifies unresolved point IDs, and records
  the converter's dropped-property counters. It is diagnostic data; the runtime
  does not yet consume those shapes.

## Verified locally

With the installed Tekken 8 build 25221600, extraction and staged import
completed. The staged pack contains the original character's model, voice,
317 converted own moves, 273 converted body clips and a 122-entry command list.
The roster contains 19 fighters, with Clive in slot 18. Clive appears in combat,
animates, deals damage and receives native body collisions. These observations
are smoke checks, not exhaustive move or collision validation.

Synthetic importer tests cover calibrated grip, independent sword motion,
translation, scale encoding and overlapping channel rejection. The original
Tag 2 primitive `039C006C` is exercised by `weapon_collision_test` against
synthetic geometry: blade reach beyond the fist, fist misses, lateral and vertical
misses, a stationary contact, a blade behind the attacker, and explicit radius.
This proves those native collision cases; it does not prove the imported shapes.

The source audit reports overlapping categories:

| Review required | Converted source moves |
| --- | ---: |
| More than two source shapes | 134 |
| Individual active windows differ from the native summary | 16 |
| Explicit radius, height or endpoint data | 166 |
| Unresolved source point codes | 6 |

## Required before completion

The source executable's point resolver (`1418CC110` in the investigated build)
and its bone-name hash lookup (`1419526F0`) establish that combat locations 120,
121 and 127 are `L_Have`, `R_Have` and `R_Have2`. These are **not** the similarly
numbered entries in `DA_OKM_Weapon_Position`, which describe visual traces.
The definition retains the combat frames separately from the rendered weapon.
The source applies endpoint offsets in the selected joint's frame even when
the radius is zero. Points 138, 139 and 141 are midpoints of right upper/lower
arm, left upper/lower arm, and left upper/lower leg respectively. These facts
must be preserved by the adapter; substituting a limb endpoint is insufficient.
The source also sweeps a single-point shape from its previous position, while
a positive height generates a vertical segment.

1. Adapt the recovered endpoint semantics to the retargeted skeleton, including
   local axes, scales, virtual midpoints, swept points and the ground-relative
   frame of source location 125. Validate those transforms against the model.
2. Feed every active shape into Tag 2's collision pipeline with its own schedule
   and dimensions. `039C0948` is the existing attack geometry wrapper;
   `039C0508` iterates segments and the defender's 14 hurt shapes, calling
   `039C006C`. A scoped adapter can preserve native guard, damage, invulnerability
   and reaction logic in the caller `03ADBD10`. No such adapter is installed yet.
3. Validate all sword visibility changes, including the back-mounted copy and
   transitions that use the animated scale tracks.
4. Import and synchronize Eikon visuals with their combat frames and special
   mechanics. Tekken 8 effects and a number of conditions/properties are still
   omitted by the existing general converter; the audit includes their counts.
5. Test reach and misses at both facings, crouch/standing/airborne victims,
   blocking, hit-stop, interrupted attacks, throws, walls, tag transitions and
   all command-list entries. Compare the blade's visible trajectory with its
   collision points frame by frame, including the native one-frame alignment.

Keep experimental packs, saves, captures and binaries separate from the normal
installation until these checks pass. The current local staged build is under
`local/clive/`; its assets and logs are ignored by Git.
