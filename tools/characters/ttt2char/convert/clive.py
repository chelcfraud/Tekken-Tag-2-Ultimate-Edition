"""Opt-in Clive mechanics backed by the native runtime's private gauge.

The source gauge is 0..200; 738 tests >=, and 0x8232 adds a signed delta.
Keep it separate from Heat and the four transient native string variables.
"""
from . import idmaps as M, tagsystem as TS

GAUGE_REQ = 0x7f00
GROUNDED_VICTIM = 0x7f01
CONTINUATION = 0x7f02
GAIN, RESET, CONTACT_GAIN, BEGIN = 0x8f00, 0x8f01, 0x8f02, 0x8f03
SOURCE_REQ, SOURCE_GAIN = 738, 0x8232


def enabled(c):
    return c.game == 't8' and c.defn.MOVESET.get('zantetsuken', False)


def gain_row(c, frame, value, requirement):
    """Encode the source's conditional gains without erasing their predicate."""
    req = M.reqs(c.k, requirement)
    if req in ([], [(0, 0)]):
        return dict(frame=frame, id=GAIN, value=value)
    if req in ([(359, 1)], [(359, 2)]) and 0 <= value <= 0xffff:
        return dict(frame=frame, id=CONTACT_GAIN, value=value | req[0][1] << 16)
    raise ValueError('unsupported Zantetsuken gain predicate: %r' % (req,))


def apply(c):
    if not enabled(c):
        return
    # Both neutral 1+4 and the Phoenix Shift version use these same lists.
    for source in ('Okm_LPRK', '#1562'):
        i = c.kn[source]
        move = c.T['moves'][c.newidx[i]]
        rows = [dict(r) for r in TS.cancels(c.T, move['cancel'])]
        restored = []
        levels = set()
        for row in M.cancels(c.k, c.k.tables['moves'][i]['cancel']):
            req = M.reqs(c.k, row['req'])
            # Keep the source meter priority, attack-to-throw eligibility,
            # hit predicate, victim state and timing. Heat activation's lock
            # has no counterpart in this character's native gauge.
            enhanced = (any(k == SOURCE_REQ for k, _ in req) and
                        ((723, 0) in req or (183, 0) in req))
            capture = req in ([(44, 0), (0x80c8, 1), (452, 0)],
                              [(47, 0), (0x80c8, 2), (452, 0)])
            if not enhanced and not capture:
                continue
            if enhanced:
                threshold=next(value for kind,value in req if kind==SOURCE_REQ)
                if threshold in levels:
                    continue
                levels.add(threshold)
                # Evaluate the native grab/hit predicates in the contact pass.
                # Variable 314 is latched one pass later, after the contact
                # owner has already been cleared, so it is only for gains.
                rq=TS.write(c.T,'requirements',[
                    dict(condition=CONTINUATION,param=threshold),
                    dict(condition=2,param=0),
                    dict(condition=46,param=0),
                    dict(condition=TS.TT_END,param=0)])
            else:
                rq, ok = c.conv_reqs(row['req'], overrides={452: 0})
                if not ok:
                    raise ValueError('cannot restore Zantetsuken contact capture: %r' % (req,))
            target = c.target(row['move_id'])
            if target is None:
                raise ValueError('missing Zantetsuken continuation')
            converted=dict(row, req=rq, move_id=target, extradata=c.extradata(row['extradata']))
            if enhanced:
                # Tag 2 can expose a one-frame strike's contact in the next
                # cancel pass. Keep animation frame 23 and permit that pass;
                # the source's 22..22 window expired before the confirmed hit.
                converted['win_end']=max(row['win_end'],row['start_frame'])
            restored.append(converted)
        if len(restored) != 6 or levels != {50,100,150,200}:
            raise ValueError('Zantetsuken source layout changed: expected four level branches and two contact latches')
        move['cancel'] = TS.write(c.T, 'cancels', restored + rows)
        props=[dict(p) for p in TS.props(c.T,move['extraprops'])]
        move['extraprops']=TS.write(c.T,'extra_move_properties',
            [dict(frame=0x8001,id=BEGIN,value=0)]+props+[dict(frame=0,id=0,value=0)])
        c.stats['Zantetsuken levels and contact captures restored'] += len(restored)
    # The normal native round-start alias runs again on round initialization.
    start = c.T['moves'][c.aliases[0]]
    props = [dict(p) for p in TS.props(c.T, start['extraprops'])]
    start['extraprops'] = TS.write(c.T, 'extra_move_properties',
        [dict(frame=0x8001, id=RESET, value=0)] + props + [dict(frame=0,id=0,value=0)])


def restore_throw_starters(c):
    """Clive's named generic throw starters carry different active windows.

    Borrowing the donor row gave the delayed starter frame 12 while its
    contact cancels ran at 15..17. Convert the actual rows and animations.
    """
    if enabled(c):
        for name in ('Thrmv_B2_00', 'Thrmv_B2_01'):
            c.cls[c.kn[name]] = 'K'
