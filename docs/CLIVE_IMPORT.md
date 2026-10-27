# Clive import status

**Experimental: Clive does not work properly. Special moves and Eikon effects
remain incomplete; full character and sword collision support has been added
and is undergoing gameplay validation. This is an unfinished prototype,
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
  the converter's dropped-property counters. Its legacy-summary comparisons are
  diagnostic data, separate from the complete runtime collision representation.
- A CRC-bound `<code>.hitboxes` sidecar preserves all eight active source shapes,
  independent windows, radii, heights and calibrated local offsets. The runtime
  evaluates them against Tag 2's native hurt capsules through `039C0508`, retaining
  native blocking, damage and reaction handling. A missing geometry entry leaves
  a donor/generic move on its original native collision path.
- Per-pose history preserves swept single-point attacks. Positive height creates
  a vertical capsule; virtual limb midpoints and ground-relative shapes retain
  their distinct meanings. Weapon frames use the same previous-frame alignment
  as the native skeleton. Tag Assault attack twins inherit the original shapes.
- Gigaflare (`uf+1+2`) imports its two actual starter rows instead of borrowing
  the donor's generic rows. Their active windows are 12-14 and 15-17; the
  latter previously had frame-12 contact followed by frame-15 continuation
  checks. Both starters retain the source throw/victim links and animations.
- Zantetsuken has a private per-actor gauge (0-200), separate from Heat and
  transient string latches. Source meter test 738 is `>=` (source executable
  case `14187C497`); source property `0x8232` adds a signed delta. The native
  adapter implements these as requirement `0x7F00` and property `0x8F00`.
  Conditional gains (`0x8F02`) retain native hit/block latch 314; whiffs do not
  earn the base 1+4 contact gain. Actor setup and the round-start alias reset
  the gauge. Tags do not consume it, and mirror opponents have separate gauges.
- Neutral and Phoenix Shift 1+4 retain all four enhanced thresholds (50, 100,
  150, 200), in source priority order. Requirement `0x7F02` tests charge at
  move entry, followed by native attack-to-throw eligibility (2) and unguarded
  contact (46). Those checks run in the actual contact pass, while the victim
  still records its attacker. Variable 314 appears on the next pass, after
  that ownership is cleared; it is used for gains, not grab activation. The
  continuation window is 22-23, with animation starting at 23.
  Property `0x8F03` snapshots charge at move entry, so the current
  strike's gain cannot prematurely select a higher level. Blocks, whiffs,
  another actor's contact and locked victims cannot start the continuation.
  Native preparation classifiers `0404F398` and `0404F3D4` recognize the
  private predicates as dynamic conditions. Previously their high ids set
  option bit 2 and silently disabled every enhanced cancel before evaluation.
  Classification of all native predicates remains unchanged.
  The source's conditional gains, timed -200 consumption, throw damage and
  victim animations are retained. Full charge selects the distinct 380-frame
  Ultimate clip first.
- The HUD is a single compact numeral below the HP bar, inset from the
  portrait. It uses alpha masks from the player's original T8 texture
  `T_UI_HUD_Pow_okm_Num`, stored locally in `clv.zanhud`. The TV scan image
  receives an alpha-blended numeral with a thin 24-by-2 progress bar underneath.
  The bar fills towards the next level, resets on a level increase, and remains
  full at level 5; the numeral and full bar are gold at that level. The active
  fighter is shown on either side, with separate
  charge for mirror opponents and tag partners. Simulation-to-GPU snapshots
  expire after combat updates stop. Both presentation paths and captures
  include the numeral. Tekken 8's Eikon effects remain incomplete.

## Verified locally

With the installed Tekken 8 build 25221600, extraction and staged import
completed. The staged pack contains the original character's model, voice,
319 converted own moves, 275 converted body clips and a 122-entry command list.
The roster contains 19 fighters, with Clive in slot 18. Clive appears in combat,
animates, deals damage and receives native body collisions. These observations
are smoke checks, not exhaustive move or collision validation.

Synthetic importer tests cover calibrated grip, independent sword motion,
translation, scale encoding and overlapping channel rejection. The original
Tag 2 primitive `039C006C` is exercised by `weapon_collision_test` against
synthetic geometry: blade reach beyond the fist, fist misses, lateral and vertical
misses, a stationary contact, a blade behind the attacker, and explicit radius.
This proves those native collision cases; it does not prove the imported shapes.

The full sidecar has also been parsed by the native test against its real
moveset CRC: 227 attack moves and 683 active shapes are retained. Tests cover
zero-radius grip offsets (the previous importer erased their reach), all eight
shapes, separate active windows and tag twins. In particular, `Okm_4LP` (b+1)
retains its 900 mm left-grip offset on frames 17-18; `Okm_6wp` and `Okm_6wp2`
(f+1+2) retain their independent frames 16-17 and 36, including the sword's
1000 mm offset. These are source-data and native-geometry checks, not a claim
that all special mechanics are implemented.

Local gameplay feedback confirms that b+1 now connects. The same test found
that f+1+2's second hit connected only at the wall and df+2 sometimes lost its
second hit. The follow-up revision resolves weapon-local samples against the
current parent transform in the collision pass and refreshes geometry even
when posing and collision share a logic-frame number; the previous sweep
endpoint stays frozen for that frame. It also retains df+2's original grounded
victim states: the inferred remap to `sDw_UP_00_` launched the victim on the
first strike instead of preserving the source stagger. Guard and airborne
entries keep their existing mapping. Automated regressions cover advancement
after weapon posing and private grounded reaction lists. Both follow-ups still
need gameplay confirmation away from walls, at both facings and several ranges.

The Gigaflare/Zantetsuken candidate also passes structural checks of both throw
starter windows, all four enhanced branches for each 1+4 variant, separate
hit/block gains, source throw damage, paired victim states and timed gauge
consumption. Native tests cover level thresholds, saturation, consumption,
independent players and reset. These checks do not replace a gameplay test of
throw contact, escape, synchronized victim animation and accumulated meter.

The user's first gameplay test confirmed Gigaflare, but 1+4 crashed. The saved
log faults at guest address `0x00001F10`, through `04E18548` and `0404FF78`:
the conditional-gain property called the complete native requirement evaluator
with a null opponent. That evaluator resolves both actors before its switch.
The property now reads the verified captured-contact word directly at
`player+0x1F8` (requirement 314 at `040570A8`: `216(player+288)`). The grounded
victim predicate likewise reads the native hit-level word at opponent+0x130,
with an explicit null guard, instead of re-entering the full evaluator.
Regression tests exercise the complete gain-property operation for whiff,
hit, block, invalid captures and consumption with no opponent dependency.
The user subsequently confirmed that charging works. The initial large HUD
was rejected and full-charge 1+4 still stayed on the normal strike, even on
an unguarded standing hit. The user accepted the compact original numeral
and requested a small progress bar, which is now drawn underneath it.

Live debugging of the user's Practice match then identified two independent
continuation failures. The four enhanced cancel rows had flags `0x47`;
`0404F398` classified their private requirement id as a native special and
set bit 2, which `0414E7E4` skips before evaluating any condition. Enabling
those rows for diagnosis revealed the second failure: at frame 22, charge
and attack-entry charge were both 200, the victim's contact owner was Clive,
and variable 314 was still 0. At frame 23, variable 314 became 1, but the
contact owner was already 0. Requiring both simultaneously could never pass.
The corrected preparation classifiers accept private dynamic predicates,
and enhanced cancels use the native grab/hit checks in the live contact pass.

`clive_cancel_test` reproduces the disabled-row result with the original
native routines, verifies the fix for each private predicate, and compares
both classifiers against the originals across native ids 0-1023, properties
and an unrelated unknown id. The actual pack retains all four thresholds,
native conditions 2/46, victim links, damage, timed consumption and the
distinct 380-frame Ultimate animation. The meter regression covers empty,
half-full and full bars, transparency and separate actor snapshots.
The user subsequently confirmed that level-five 1+4 executes Ultimate.
The same Practice session's trace selected threshold 200, target 2306
(`Okm_#1565`), on frame 22, starting the continuation at frame 23. Its gauge
consumption ran from that move on frame 266 (`-200`, charge returned to 0),
and the match continued to accept normal attacks afterwards. The trace also
confirmed the lower threshold-50 continuation and its frame-150 consumption.

The Clive changes are based on Petexy's `codex/armor-king-t8-moves`
through `9ee2e52`, including `390eac3` (Reina bounds, Tag Assault strings and
assist control) and the optional Armor King T8 moves. The conflict in Tag
Assault generation retains the upstream finish-hit/string rules and Clive's
collision-twin mapping. Published `main` history is retained when reconciling
the rebased work, allowing a normal push without replacing remote history.

See [Clive runtime support](CLIVE_RUNTIME.md) for the complete change inventory,
sidecar formats, pack upgrade instructions, diagnostics and repeatable checks.

The original legacy-summary audit reports overlapping categories below. The
new runtime sidecar handles this geometry instead of relying on that summary:

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

1. Continue validating the retargeted local axes, scales, virtual midpoints,
   swept points and ground-relative frame of source location 125 against the
   model at both facings and across state transitions.
2. Expand gameplay regression coverage for the installed collision adapter.
   `039C0948` is the existing attack geometry wrapper;
   `039C0508` iterates segments and the defender's 14 hurt shapes, calling
   `039C006C`. The scoped radius adapter and geometry hook preserve guard,
   damage, invulnerability and reaction logic in the caller `03ADBD10`.
3. Validate all sword visibility changes, including the back-mounted copy and
   transitions that use the animated scale tracks.
4. Import and synchronize Eikon visuals with their combat frames and special
   mechanics. Tekken 8 effects and a number of conditions/properties are still
   omitted by the existing general converter; the audit includes their counts.
5. Test reach and misses at both facings, crouch/standing/airborne victims,
   blocking, hit-stop, interrupted attacks, throws, walls, tag transitions and
   all command-list entries. Compare the blade's visible trajectory with its
   collision points frame by frame, including the native one-frame alignment.

Build and inspect candidate packs under `local/clive/` before local testing.
The user's normal installation has a backed-up candidate for manual testing;
this deployment does not establish that all checks above pass. Packs, saves,
captures, backups and binaries are ignored by Git.
