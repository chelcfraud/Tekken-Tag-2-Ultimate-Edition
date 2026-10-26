"""Record collision information the legacy four-byte hitbox cannot represent.

This is a diagnostic, not a collision converter. Keep the complete source
shapes beside an experimental pack so a successful import cannot be confused
with validation of its combat geometry.
"""
import collections


def report(converter):
    moves = []
    counts = collections.Counter()
    source = converter.k
    for original, target in sorted(converter.newidx.items()):
        shapes = source.hitboxes(original)
        if not shapes:
            continue
        row = converter.T['moves'][target]
        reasons = []
        if len(shapes) > 2:
            reasons.append('more_than_two_shapes')
        if any((h.first, h.last) != (row['first_active'], row['last_active']) for h in shapes):
            reasons.append('individual_active_windows')
        if any(h.radius or h.height or any(h.a) or any(h.b) for h in shapes):
            reasons.append('explicit_geometry')
        unresolved = sorted({x for h in shapes for x in (h.loc, h.loc2)
                             if converter.hit_location(x) > 77})
        if unresolved:
            reasons.append('unresolved_locations')
        counts.update(reasons)
        moves.append(dict(source_move=original, target_move=target, name=source.move_name(original),
            source_hitboxes=[h._asdict() for h in shapes],
            native_summary=list(row['hitbox']), native_first=row['first_active'],
            native_last=row['last_active'], unresolved_locations=unresolved, review_required=reasons))
    return dict(format=1, status='incomplete' if counts else 'geometry_review_required',
        description='Diagnostic only; source geometry has not been validated against native collision.',
        affected_moves=dict(sorted(counts.items())), moves=moves,
        conversion_counters=dict(sorted(converter.stats.items())))
