"""Opt-in Clive mechanics backed by the native runtime's private gauge.

The source gauge is 0..200; 738 tests >=, and 0x8232 adds a signed delta.
Keep it separate from Heat and the four transient native string variables.
"""
from . import idmaps as M, tagsystem as TS

GAUGE_REQ = 0x7f00
GROUNDED_VICTIM = 0x7f01
CONTINUATION = 0x7f02
HELD_CHARGE = 0x7f03
GAIN, RESET, CONTACT_GAIN, BEGIN = 0x8f00, 0x8f01, 0x8f02, 0x8f03
CHARGE_BEGIN = 0x8f04
GUARD_BROKEN = 0x8f05
SOURCE_REQ, SOURCE_GAIN = 738, 0x8232
HURT_X, HURT_YZ, HURT_SIZE, HURT_CLEAR = 0x8f10, 0x8f11, 0x8f12, 0x8f13


def restore_pickup_hurtbox(c):
    """Keep d+1+2 CH's temporary auxiliary hurt capsule on its victim.

    T8 8375/8376 configure/disable an extra hurt capsule, not a visual effect.
    The victim can be any character; the marker belongs to the reaction move.
    Resolve that reaction from the hit list, never from an unstable unnamed ID.
    """
    if not c.defn.MOVESET.get('clive_pickup_hurtbox'):
        return
    attack=c.k.tables['moves'][c.kn['Okm_2WP']]
    hits=list(M.hitconds(c.k,attack['hit_condition']))
    reactions=[r for guards,_,r in hits if guards in ([],[(0,0)])]
    if len(reactions)!=1:
        raise ValueError('unsupported Clive d+1+2 hit list')
    source=c.k.resolve_alias(c.k.tables['reactions'][reactions[0]]['ch'])
    target=c.target(source)
    if target is None:
        raise ValueError('missing Clive d+1+2 counter reaction')
    props=TS.props(c.k.tables,c.k.tables['moves'][source]['extraprops'])
    auxiliary=[p for p in props if p['id'] in (0x8375,0x8376)]
    # Do not silently apply this adapter to a changed source layout.
    if ([p['id'] for p in auxiliary]!=[0x8375,0x8376] or
        any(M.reqs(c.k,p['req']) not in ([],[(0,0)]) for p in auxiliary) or
        any(p['value'] for p in auxiliary)):
        raise ValueError('unsupported Clive counter-hit auxiliary capsule')
    rows=[dict(frame=0x8001,id=HURT_CLEAR,value=0)]
    for p in auxiliary:
        if p['id']==0x8375:
            rows += [dict(frame=p['frame'],id=idv,value=p[field]) for idv,field in
                     ((HURT_X,'value'),(HURT_YZ,'value2'),(HURT_SIZE,'value3'))]
        else:
            rows.append(dict(frame=p['frame'],id=HURT_CLEAR,value=0))
    move=c.T['moves'][target]
    move['extraprops']=TS.write(c.T,'extra_move_properties',
        rows+[dict(p) for p in TS.props(c.T,move['extraprops'])]+[dict(frame=0,id=0,value=0)])
    c.stats['Clive counter-hit pickup capsule restored']+=1


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


def restore_charged_string(c):
    """f+2,2,1: replace this branch's Heat gate with level 5 only.

    Keep the source charge animation, release timing, 25/30 damage and
    normal/guard-break reactions. A runtime latch tracks held LP through
    source frame 21; native transient variable 313 is not the charge state.
    """
    if not enabled(c) or not c.defn.MOVESET.get('clive_charged_string'):
        return
    source = c.kn['Okm_6rprp']
    branches = [r for r in M.cancels(c.k, c.k.tables['moves'][source]['cancel'])
                if r['button'] == 0x40000001 and (1028, 1) in M.reqs(c.k, r['req'])]
    if len(branches) != 1:
        raise ValueError('unsupported Clive f+2,2,1 Heat branch')
    branch = branches[0]
    charge_end = [r for r in M.cancels(c.k,c.k.tables['moves'][branch['move_id']]['cancel'])
                  if M.reqs(c.k,r['req'])==[(358,0),(0x8246,5120)]]
    if len(charge_end)!=1 or charge_end[0]['win_start']!=charge_end[0]['win_end']:
        raise ValueError('unsupported Clive charged string hold window')
    # Convert the remaining predicates normally, including any source actions.
    remaining = [dict(r) for kind, _, r in c.req_rows(branch['req']) if kind != 1028]
    at = len(c.k.tables['requirements'])
    c.k.tables['requirements'] += remaining + [dict(condition=c.end, param=0)]
    rq, ok = c.conv_reqs(at)
    if not ok:
        raise ValueError('unsupported Clive f+2,2,1 input predicate')
    rq = TS.write(c.T, 'requirements', [dict(condition=GAUGE_REQ, param=200)] +
                  [dict(condition=q, param=p) for q,p in TS.reqs(c.T,rq)] +
                  [dict(condition=TS.TT_END, param=0)])
    target = c.target(branch['move_id'])
    if target is None:
        raise ValueError('missing Clive charged string finisher')
    starter = c.T['moves'][c.newidx[source]]
    route = dict(branch, req=rq, move_id=target, extradata=c.extradata(branch['extradata']))
    starter['cancel'] = TS.write(c.T, 'cancels', [route] +
                                [dict(r) for r in TS.cancels(c.T,starter['cancel'])])
    finisher = c.T['moves'][target]
    hits, charged = [], 0
    for h in TS.hits(c.T, finisher['hit_condition']):
        guards = TS.reqs(c.T,h['req'])
        if (313,0) in guards:
            charged += 1
            guards = [(HELD_CHARGE,200) if (q,p)==(313,0) else (q,p) for q,p in guards]
            h = dict(h,req=TS.write(c.T,'requirements',
                     [dict(condition=q,param=p) for q,p in guards]+[dict(condition=TS.TT_END,param=0)]))
        hits.append(dict(h))
    if charged != 2 or len(hits) != 4:
        raise ValueError('unsupported Clive charged finisher hit list')
    # The grounded charged branch must retain the source guard-break reaction.
    guard = c.T['reactions'][hits[1]['reactions']]['block']
    source_hits = M.hitconds(c.k,c.k.tables['moves'][branch['move_id']]['hit_condition'])
    expected = c.target(c.k.tables['reactions'][source_hits[1][2]]['block'])
    if guard != expected or guard == 0:
        raise ValueError('missing Clive charged guard-break reaction')
    # Isolate this string: #334 is shared with other attacks. At contact
    # frames 26..27 and attacker recovery 60, victim recovery 47 gives
    # +13..14, below Clive's i15 standing launchers even on a late hit.
    reaction_move = dict(c.T['moves'][guard],name=c.string('Okm_CliveGuardBreak'))
    recovery = [dict(r) for r in TS.cancels(c.T,reaction_move['cancel'])]
    attack_end = TS.cancels(c.T,finisher['cancel'])[-1]
    until = attack_end['win_start']-finisher['last_active']+14
    if (recovery[-1]['direction']!=M.LIST_END or attack_end['direction']!=M.LIST_END or
        until<=recovery[-1]['win_start'] or finisher['first_active']>finisher['last_active']):
        raise ValueError('unsupported Clive guard-break recovery window')
    recovery[-1].update(win_start=until,start_frame=until)
    reaction_move['cancel'] = TS.write(c.T,'cancels',recovery)
    props = [dict(p) for p in TS.props(c.T,reaction_move['extraprops'])]
    reaction_move['extraprops'] = TS.write(c.T,'extra_move_properties',
        [dict(frame=0x8001,id=GUARD_BROKEN,value=0)]+props+[dict(frame=0,id=0,value=0)])
    guard = c.add('moves',reaction_move)
    reaction = dict(c.T['reactions'][hits[1]['reactions']],block=guard)
    hits[1]['reactions'] = c.add('reactions',reaction)
    finisher['hit_condition'] = TS.write(c.T,'hit_conditions',hits)
    props = [dict(p) for p in TS.props(c.T,finisher['extraprops'])]
    finisher['extraprops'] = TS.write(c.T,'extra_move_properties',
        [dict(frame=0x8001,id=CHARGE_BEGIN,value=charge_end[0]['win_start'])]+props+[dict(frame=0,id=0,value=0)])
    c.stats['Clive level-5 charged guard-break string restored'] += 1


def restore_air_string(c):
    """Carry uf+2's input/contact latches across its three attack rows.

    Like Noctis, use native persistent words, not the transient string
    variables cleared by each move change. Reset only at the starter.
    The source's bit 0 is RP and bit 2 is contact; both gate the finisher.
    """
    if not c.defn.MOVESET.get('clive_air_string'):
        return
    from . import specialcancels as S

    def req(values):
        return TS.write(c.T, 'requirements',
                        [dict(condition=q, param=p) for q, p in values]
                        + [dict(condition=TS.TT_END, param=0)])

    chain = ('Okm_9RP', 'Okm_9RP2', 'Okm_9RP3')
    for name in chain:
        source = c.k.tables['moves'][c.kn[name]]
        original = M.cancels(c.k, source['cancel'])
        move = c.T['moves'][c.newidx[c.kn[name]]]
        captures, dispatch = [], []
        replaced = []
        for row in original:
            guards = M.reqs(c.k, row['req'])
            if guards == [(0x815a, 0)] and row['button']:
                checks = [(S.SPECIAL_SET, 1)]
            elif guards == [(43, 0), (0x815a, 2), (0x815a, 3)]:
                checks = [(46, 0), (S.CONTACT_SET, 1)]
            elif guards == [(507, 0), (507, 2)]:
                target = c.target(row['move_id'])
                if target is None:
                    raise ValueError('missing Clive airborne finisher')
                dispatch.append(dict(row, req=req([(S.SPECIAL_VAR, 1), (S.CONTACT_VAR, 1)]),
                                     extradata=c.extradata(row['extradata']), move_id=target))
                continue
            else:
                continue
            replaced.append(row)
            captures.append(dict(row, req=req(checks), extradata=c.extradata(row['extradata']),
                                 move_id=0x8001, option=0))
        if len(captures) != 2 or len(dispatch) != (1 if name == chain[-1] else 0):
            raise ValueError('unsupported Clive airborne string layout: ' + name)
        def same_window(row, old):
            return all(row[f] == old[f] for f in
                       ('direction', 'button', 'win_start', 'win_end', 'start_frame'))
        body = [dict(row) for row in TS.cancels(c.T, move['cancel'])
                if not any(same_window(row, old) for old in replaced)]
        move['cancel'] = TS.write(c.T, 'cancels', captures + dispatch + body)
        c.stats['Clive airborne string rows restored'] += len(captures) + len(dispatch)
    starter = c.T['moves'][c.newidx[c.kn[chain[0]]]]
    entry = []
    if starter.get('begin_props') is not None:
        for prop in c.T['move_begin_props'][starter['begin_props']:]:
            if prop['id'] == TS.TT_END:
                break
            entry.append(dict(prop))
    empty = req([])
    starter['begin_props'] = TS.write(c.T, 'move_begin_props',
        [dict(req=empty, id=S.SPECIAL_SET, value=0),
         dict(req=empty, id=S.CONTACT_SET, value=0)] + entry
        + [dict(req=empty, id=TS.TT_END, value=0)])
