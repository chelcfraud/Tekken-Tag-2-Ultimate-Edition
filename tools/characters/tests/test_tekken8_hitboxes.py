"""Full sword reach and every active volume survive the legacy-summary limit."""
import os
import struct
import sys
import types
import unittest
import zlib

import numpy as np

HERE=os.path.dirname(__file__)
sys.path[:0]=[HERE,os.path.join(HERE,'..')]
import test_retarget as TR
from ttt2char.tekken8 import hitboxes, motbin
from ttt2char.ttt2 import bone


def shape(first,last,loc=121,loc2=0,a=(0,1000,0),b=(0,0,0),radius=0,height=0):
    return motbin.Hitbox(first,last,loc,loc2,0,radius,height,a,b,0)


class FullHitboxes(unittest.TestCase):
    def setUp(self):
        self.target=TR.ttt2_bon()
        self.a=types.SimpleNamespace(sk=types.SimpleNamespace(names=['R_Have','L_Have','R_Have2']),
            weapons=[dict(joint=i,pair=4+i,rotation=np.eye(3),parent_scale=1.) for i in range(3)],
            cal=types.SimpleNamespace(offsets={n:np.eye(3) for n in ('TE_R_jnt','TE_L_jnt','UDE_L_jnt','KATA_L_jnt')}))

    def converter(self,shapes):
        rows=[dict(first_active=16,last_active=17,hitbox=bytes([70,0,70,70]),move_id_hi=82,move_id_lo=i)
              for i in range(3)]
        source=types.SimpleNamespace(hitboxes=lambda i:shapes)
        return types.SimpleNamespace(k=source,newidx={0:0},T={'moves':rows},
            collision_twins={1:0},hit_location=lambda n:n)

    def test_eight_shapes_and_later_windows_and_tag_twins_survive(self):
        source=[shape(16,17),shape(16,17,loc2=121),shape(16,17,a=(0,300,0)),
                shape(16,17,radius=10)]+[shape(36+i,36+i) for i in range(4)]
        c=self.converter(source)
        data=hitboxes.bind(hitboxes.build(c,self.a,self.target),b'final moveset')
        magic,version,crc,count=struct.unpack_from('<4sIII',data)
        self.assertEqual((magic,version,crc,count),(b'T8HB',1,zlib.crc32(b'final moveset'),2))
        key,n=struct.unpack_from('<II',data,16)
        self.assertEqual((key,n),(82<<16,8))
        size=hitboxes.SHAPE.size+2*hitboxes.ENDPOINT.size
        self.assertEqual(struct.unpack_from('<II',data,24+7*size),(39,39))
        self.assertEqual(c.T['moves'][0]['last_active'],39)
        self.assertEqual(c.T['moves'][1]['last_active'],39)
        self.assertEqual(c.T['moves'][2]['last_active'],17) # no attack added to an unrelated move
        a=hitboxes.ENDPOINT.unpack_from(data,24+hitboxes.SHAPE.size)
        self.assertEqual(a[:2],(2,4))
        np.testing.assert_allclose(a[5:8],(0,1000,0)) # zero radius must NOT erase blade reach
        b=hitboxes.ENDPOINT.unpack_from(data,24+hitboxes.SHAPE.size+hitboxes.ENDPOINT.size)
        self.assertEqual(b[0],5) # swept point, rather than an endpoint at the origin

    def test_back_one_keeps_the_left_grip_reach(self):
        c=self.converter([shape(17,18,loc=120,a=(0,900,0))])
        data=hitboxes.build(c,self.a,self.target)
        a=hitboxes.ENDPOINT.unpack_from(data,24+hitboxes.SHAPE.size)
        self.assertEqual(a[:2],(2,5))
        np.testing.assert_allclose(a[5:8],(0,900,0))

    def test_clive_f2_contact_adaptation_covers_variants_but_not_other_attacks(self):
        c=self.converter([shape(15,15,loc2=121),shape(15,15,radius=20)])
        c.defn=types.SimpleNamespace(MOVESET={'clive_f2_contact_margin':True})
        c.kn={'Okm_rp00F':0}
        c.k.anim_ref=lambda i:(123 if i<2 else 456,False)
        c.newidx={0:0,1:1,2:2};c.collision_twins={}
        data=hitboxes.build(c,self.a,self.target)
        at=16
        for i in range(3):
            _,count=struct.unpack_from('<II',data,at);at+=8
            for _ in range(count):
                first,last,radius,height=hitboxes.SHAPE.unpack_from(data,at)
                self.assertEqual((first,last),(15,16) if i<2 else (15,15))
                self.assertEqual(radius,100. if i<2 else (0. if _==0 else 20.))
                at+=hitboxes.SHAPE.size+2*hitboxes.ENDPOINT.size
        c.defn.MOVESET.clear()
        original=hitboxes.build(c,self.a,self.target)
        self.assertEqual(hitboxes.SHAPE.unpack_from(original,24)[:3],(15,15,0.))

    def test_virtual_midpoint_is_not_replaced_by_limb_endpoint(self):
        endpoint=hitboxes.Endpoints(self.converter([]),self.a,self.target).endpoint(139,(0,0,0))
        self.assertEqual(endpoint[:3],(3,11,12))
        self.assertNotEqual(endpoint[3],endpoint[4])

    def test_offset_is_calibrated_to_the_target_joint_axes_and_scale(self):
        self.a.weapons[0]['rotation']=TR.rot_about([0,0,1],np.pi/2)
        self.a.weapons[0]['parent_scale']=2.
        endpoint=hitboxes.Endpoints(self.converter([]),self.a,self.target).endpoint(121,(0,1000,0))
        np.testing.assert_allclose(endpoint[5:8],(500,0,0),atol=1e-10)


if __name__=='__main__':unittest.main()
