"""Zantetsuken keeps its resource gates, contact gains and throw timing."""
import os
import sys
import types
import unittest
import struct
import numpy as np

sys.path[:0]=[os.path.dirname(__file__),os.path.join(os.path.dirname(__file__),'..')]
from test_tekken8_convert import Source8, converter
from ttt2char.convert import clive, tagsystem as TS
from ttt2char.tekken8 import clive_hud


class CliveMechanics(unittest.TestCase):
    def test_charged_string_requires_level_five_and_preserves_tap_and_guard_reactions(self):
        k,c=self.fixture()
        c.defn.MOVESET['clive_charged_string']=True
        c.str_off={};c.strings=b''
        empty=k.req()
        route=dict(direction=0,button=0x40000001,req=k.req((1028,1),(0x834c,1)),extradata=0,
                   win_start=1,win_end=25,start_frame=25,move_id=1,option=0)
        end=dict(route,direction=0x8000,button=0,req=empty,move_id=0x8001)
        charge=dict(end,direction=0,req=k.req((358,0),(0x8246,5120)),win_start=21,win_end=21)
        k.tables['cancels']=[route,end,charge,end]
        k.tables['moves']=[dict(cancel=0),dict(cancel=2,hit_condition=0)]
        k.tables['hit_conditions']=[dict(req=k.req((358,0)),damage=30,reactions=0),dict(req=empty,damage=30,reactions=0)]
        k.tables['reactions']=[dict(block=7)]
        c.kn={'Okm_6rprp':0};c.newidx={0:0}
        c.target=lambda i:{1:1,7:2}.get(i)
        c.extradata=lambda i:i
        c.T['cancels']=[dict(end,req=TS.write(c.T,'requirements',[dict(condition=TS.TT_END,param=0)]))]
        hits=[]
        for guards,damage,reaction in [([(466,0),(313,0)],30,0), ([(313,0)],30,0),
                                        ([(466,0)],25,1), ([],25,1)]:
            rq=TS.write(c.T,'requirements',[dict(condition=q,param=p) for q,p in guards]+[dict(condition=TS.TT_END,param=0)])
            hits.append(dict(req=rq,damage=damage,reactions=reaction))
        c.T['hit_conditions']=hits;c.T['reactions']=[dict(block=2),dict(block=3)]
        native_empty=c.T['cancels'][0]['req']
        attack_end=TS.write(c.T,'cancels',[dict(end,req=native_empty,win_start=60,start_frame=60)])
        guard_end=TS.write(c.T,'cancels',[dict(end,req=native_empty,win_start=45,start_frame=45)])
        c.T['moves']=[dict(cancel=0),dict(hit_condition=0,extraprops=None,cancel=attack_end,first_active=26,last_active=27),
                      dict(extraprops=None,cancel=guard_end)]
        clive.restore_charged_string(c)
        route=TS.cancels(c.T,c.T['moves'][0]['cancel'])[0]
        self.assertEqual(TS.reqs(c.T,route['req']),[(clive.GAUGE_REQ,200)])
        self.assertEqual((route['button'],route['move_id'],route['win_start'],route['win_end'],route['start_frame']),
                         (0x40000001,1,1,25,25))
        hits=TS.hits(c.T,c.T['moves'][1]['hit_condition'])
        self.assertEqual([TS.reqs(c.T,h['req']) for h in hits],
                         [[(466,0),(clive.HELD_CHARGE,200)],[(clive.HELD_CHARGE,200)],[(466,0)],[]])
        self.assertEqual([h['damage'] for h in hits],[30,30,25,25])
        self.assertEqual([h['reactions'] for h in hits],[0,2,1,1])
        self.assertEqual(c.T['reactions'][0]['block'],2) # shared reaction stays unchanged
        new_guard=c.T['reactions'][2]['block']
        self.assertEqual(new_guard,3)
        self.assertEqual(TS.cancels(c.T,c.T['moves'][2]['cancel'])[-1]['win_start'],45)
        until=TS.cancels(c.T,c.T['moves'][new_guard]['cancel'])[-1]['win_start']
        self.assertEqual(until,47)
        self.assertEqual([until-(60-hit) for hit in (26,27)],[13,14])
        self.assertEqual(TS.props(c.T,c.T['moves'][new_guard]['extraprops'])[0],
                         dict(frame=0x8001,id=clive.GUARD_BROKEN,value=0))
        self.assertEqual(TS.props(c.T,c.T['moves'][1]['extraprops'])[0],
                         dict(frame=0x8001,id=clive.CHARGE_BEGIN,value=21))

    def test_counter_pickup_preserves_auxiliary_volume_and_window_on_victim(self):
        k,c=self.fixture()
        c.defn.MOVESET['clive_pickup_hurtbox']=True
        empty=k.req()
        at=k.props((45,0x8375,0,empty,0x00640190),(60,0x8376,0,empty))
        k.tables['extra_move_properties'][at]['value2']=950
        k.tables['moves']=[dict(hit_condition=0),dict(extraprops=at)]
        k.tables['hit_conditions']=[dict(req=empty,damage=23,reactions=0)]
        k.tables['reactions']=[dict(ch=1)]
        c.kn={'Okm_2WP':0};c.target=lambda i:2
        c.T['moves']=[dict(extraprops=None) for _ in range(3)]
        clive.restore_pickup_hurtbox(c)
        self.assertIsNone(c.T['moves'][0]['extraprops'])
        self.assertEqual(TS.props(c.T,c.T['moves'][2]['extraprops']),[
            dict(frame=0x8001,id=clive.HURT_CLEAR,value=0),
            dict(frame=45,id=clive.HURT_X,value=0),
            dict(frame=45,id=clive.HURT_YZ,value=950),
            dict(frame=45,id=clive.HURT_SIZE,value=0x00640190),
            dict(frame=60,id=clive.HURT_CLEAR,value=0)])
        k.tables['extra_move_properties'][at]['req']=k.req((359,1))
        with self.assertRaisesRegex(ValueError,'auxiliary capsule'):
            clive.restore_pickup_hurtbox(c)

    def test_owned_numerals_skip_empty_cell_and_preserve_alpha(self):
        image=np.zeros((256,1536,4),np.uint8)
        for level in range(6):image[:,256*level:256*(level+1),3]=30*level
        data=clive_hud.encode(image)
        self.assertEqual(struct.unpack_from('<4sIII',data),(b'ZHUD',1,128,128))
        self.assertEqual(len(data),16+5*128*128)
        self.assertEqual([data[16+i*128*128] for i in range(5)],[30,60,90,120,150])
        with self.assertRaisesRegex(ValueError,'layout'):clive_hud.encode(image[:128])
    def fixture(self):
        k=Source8()
        c=converter(k,req={2:2,44:46,723:466,359:314,47:49},prop={0x80c8:0x8099})
        c.defn=types.SimpleNamespace(MOVESET={'zantetsuken':True})
        return k,c

    def test_meter_requirement_and_signed_action_survive(self):
        k,c=self.fixture()
        rq,ok=c.conv_reqs(k.req((738,150),(0x8232,0xffffff38)))
        self.assertTrue(ok)
        self.assertEqual(TS.reqs(c.T,rq),[(clive.GAUGE_REQ,150),(clive.GAIN,0xffffff38)])
        # Opt-in is scoped: other characters still lack a native meter.
        c.defn=types.SimpleNamespace(MOVESET={});c.cache={}
        self.assertFalse(c.conv_reqs(k.req((738,150)))[1])

    def test_hit_and_block_gains_keep_distinct_predicates(self):
        k,c=self.fixture()
        i=k.props((23,0x8232,10,k.req((359,1))),
                  (23,0x8232,5,k.req((359,2))),
                  (150,0x8232,0xffffff38,k.req((0,0))))
        at=c.conv_xps(i)
        self.assertEqual(TS.props(c.T,at),[
            dict(frame=23,id=clive.CONTACT_GAIN,value=0x1000a),
            dict(frame=23,id=clive.CONTACT_GAIN,value=0x20005),
            dict(frame=150,id=clive.GAIN,value=0xffffff38)])
        with self.assertRaisesRegex(ValueError,'predicate'):
            clive.gain_row(c,23,10,k.req((359,3)))

    def test_all_levels_keep_source_priority_contact_and_timing(self):
        k,c=self.fixture()
        k.tables['moves']=[dict(cancel=0),dict(cancel=0)]
        source=[]
        for threshold,target in [(200,2),(150,3),(100,4),(50,5)]:
            source.append(dict(direction=0,button=0,req=k.req((738,threshold),(2,0),(44,0),(723,0),(452,0)),
                extradata=0,win_start=22,win_end=22,start_frame=23,move_id=target,option=0))
            source.append(dict(source[-1],req=k.req((738,threshold),(2,0),(44,0),(183,0),(452,0))))
        for contact,value in [(44,1),(47,2)]:
            source.append(dict(source[0],req=k.req((contact,0),(0x80c8,value),(452,0)),
                win_start=1,win_end=32767,start_frame=1,move_id=0x8001))
        source.append(dict(source[0],direction=0x8000,req=k.req((0,0)),move_id=0x8001))
        k.tables['cancels']=source
        c.kn={'Okm_LPRK':0,'#1562':1};c.newidx={0:0,1:1};c.aliases=[2]
        c.T['moves']=[dict(cancel=0,extraprops=None),dict(cancel=0,extraprops=None),dict(extraprops=None)]
        end=dict(source[-1],req=c.conv_reqs(source[-1]['req'])[0])
        c.T['cancels']=[end]
        c.target=lambda i:i+100 if i<0x8000 else i
        c.extradata=lambda i:i
        clive.apply(c)
        for move in c.T['moves'][:2]:
            rows=TS.cancels(c.T,move['cancel'])
            self.assertEqual([TS.reqs(c.T,r['req']) for r in rows[:4]],
                [[(clive.CONTINUATION,n),(2,0),(46,0)] for n in (200,150,100,50)])
            for r in rows[:4]:
                self.assertEqual((r['win_start'],r['win_end'],r['start_frame']),(22,23,23))
            self.assertEqual(rows[0]['move_id'],102) # full charge selects Ultimate first
            self.assertEqual(TS.props(c.T,move['extraprops']),[dict(frame=0x8001,id=clive.BEGIN,value=0)])
        self.assertEqual(TS.props(c.T,c.T['moves'][2]['extraprops']),[dict(frame=0x8001,id=clive.RESET,value=0)])

    def test_generic_gigaflare_starters_are_imported_as_own_rows(self):
        _,c=self.fixture()
        c.kn={'Thrmv_B2_00':0,'Thrmv_B2_01':1};c.cls=['G','G','G']
        clive.restore_throw_starters(c)
        self.assertEqual(c.cls,['K','K','G'])

    def test_shared_reaction_opt_in_prevents_neutral_and_air_fallbacks(self):
        from ttt2char.characters import clive as definition
        for name in definition.MOVESET['preserve_reactions']:
            k=Source8({0:name},[(1,1)])
            c=converter(k)
            c.defn=types.SimpleNamespace(MOVESET=definition.MOVESET)
            c.newidx={};c.delta_move={};c.dn={'motOrigin':0,'Dw_AIR00_Png':1}
            c.react_remap={name:'motOrigin'}
            c.cls=['T'];c.alloc_ok=1;c.T['moves']=[{},{}];c.queue=[]
            c.conv_move=lambda i:dict(source=i)
            # All slots/lists resolve to the same imported source state.
            self.assertEqual(c.target(0),2)
            self.assertEqual(c.target(0),2)
            self.assertEqual(c.queue,[0])
            self.assertEqual(c.T['moves'][2],dict(source=0))
            # No change to the shared evidence or other characters.
            self.assertEqual(c.react_remap,{name:'motOrigin'})
            c.newidx={};c.defn=types.SimpleNamespace(MOVESET={})
            self.assertEqual(c.target(0),0)

    def test_air_string_keeps_input_and_contact_until_finisher(self):
        from ttt2char.convert import specialcancels as S
        k,c=self.fixture()
        c.defn.MOVESET['clive_air_string']=True
        c.kn={name:i for i,name in enumerate(('Okm_9RP','Okm_9RP2','Okm_9RP3'))}
        c.newidx={i:i for i in range(3)}
        c.target=lambda i:i
        c.extradata=lambda i:i
        k.tables['moves']=[];k.tables['cancels']=[]
        c.T['moves']=[];c.T['cancels']=[]
        c.T['move_begin_props']=[]
        for i in range(3):
            row=dict(direction=0,button=0,req=k.req((0,0)),extradata=0,
                     win_start=1,win_end=32767,start_frame=1,move_id=0x8001,option=0)
            src=[dict(row,button=0x40000002,req=k.req((0x815a,0))),
                 dict(row,req=k.req((43,0),(0x815a,2),(0x815a,3)))]
            if i==2:
                src.append(dict(row,req=k.req((507,0),(507,2)),win_start=34,
                                win_end=34,start_frame=34,move_id=3,extradata=1))
            src.append(dict(row,direction=0x8000,win_start=66,start_frame=66))
            k.tables['moves'].append(dict(cancel=TS.write(k.tables,'cancels',src)))
            # The old converter kept empty input/contact actions but dropped dispatch.
            body=[dict(src[0],req=TS.write(c.T,'requirements',[dict(condition=690,param=0)])),
                  dict(src[1],req=TS.write(c.T,'requirements',
                       [dict(condition=46,param=0),dict(condition=690,param=0)])),
                  dict(src[-1],req=TS.write(c.T,'requirements',
                       [dict(condition=0,param=0),dict(condition=690,param=0)]))]
            c.T['moves'].append(dict(cancel=TS.write(c.T,'cancels',body),begin_props=None))
        clive.restore_air_string(c)
        for i,move in enumerate(c.T['moves']):
            rows=TS.cancels(c.T,move['cancel'])
            self.assertEqual(TS.reqs(c.T,rows[0]['req']),[(S.SPECIAL_SET,1)])
            self.assertEqual(TS.reqs(c.T,rows[1]['req']),[(46,0),(S.CONTACT_SET,1)])
            self.assertEqual(len(rows),4 if i==2 else 3)
            if i:
                self.assertIsNone(move['begin_props']) # internal transitions must retain latches
        finish=TS.cancels(c.T,c.T['moves'][2]['cancel'])[2]
        self.assertEqual(TS.reqs(c.T,finish['req']),[(S.SPECIAL_VAR,1),(S.CONTACT_VAR,1)])
        self.assertEqual(tuple(finish[f] for f in ('win_start','win_end','start_frame','move_id','extradata')),
                         (34,34,34,3,1))
        reset=c.T['move_begin_props'][c.T['moves'][0]['begin_props']:]
        self.assertEqual([(p['id'],p['value']) for p in reset[:2]],[(S.SPECIAL_SET,0),(S.CONTACT_SET,0)])


if __name__=='__main__':unittest.main()
