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


if __name__=='__main__':unittest.main()
