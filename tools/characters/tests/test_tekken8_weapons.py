"""Weapon motion follows the retargeted hand without losing its own translation or swing."""
import os
import sys
import types
import unittest

import numpy as np

HERE = os.path.dirname(__file__)
sys.path[:0] = [HERE, os.path.join(HERE, '..')]
import test_retarget as TR
import test_tekken8_anim as TA
from ttt2char.convert import retarget, weapons
from ttt2char.tekken8 import anim, panm
from ttt2char.ttt2 import animation, bone
from ttt2char import pack


class WeaponMotion(unittest.TestCase):
    def setUp(self):
        self.target = TR.ttt2_bon()
        self.fighter = TA.Fighter(self.target)
        src = self.fighter.sk
        parent = src.index['R_Hand']
        self.source = retarget.Skeleton(src.names+['Sword'], src.parents+[parent],
            np.vstack([src.t,[100.,0.,0.]]), np.concatenate([src.R,np.eye(3)[None]]),
            np.vstack([src.s,[1.,1.,1.]]))
        self.bind_t = np.array([70.,20.,-10.])
        self.bind_R = TR.rot_about([0,0,1],0.3)
        self.target = dict(self.target,
            names=self.target['names']+['cha:OPT800_Sword'],
            parent=self.target['parent']+[self.target['names'].index('cha:TE_R_jnt')],
            t=np.vstack([self.target['t'],self.bind_t]),
            r=np.vstack([self.target['r'],bone.euler_xyz_from_matrix(self.bind_R)]),
            s=np.vstack([self.target['s'],np.ones(3)]))
        self.spec = dict(bone='Sword',parent='TE_R_jnt',source_parent='R_Hand',pair=0)
        self.converter = anim.Converter(self.source,self.target,weapons=[self.spec])

    def test_resting_weapon_keeps_its_grip_while_the_body_moves(self):
        blob = self.fighter.clip(TR.smooth_values(24))
        out,_ = self.converter.channels(panm.Animation(blob))
        self.assertEqual(out.shape,(24,25,3))
        np.testing.assert_allclose(out[:,23],np.broadcast_to(self.bind_t,(24,3)),atol=1e-6)
        rotations=animation.local_rotation(out[:,24],animation.COMPRESSED)
        self.assertLess(retarget.angle(rotations,self.bind_R).max(),1e-5)
        encoded=self.converter.animation(blob)
        self.assertEqual(animation.header(encoded)['nch'],25)
        decoded=animation.decode(encoded)['values']
        np.testing.assert_allclose(decoded[:,23],out[:,23],atol=0.02)
        self.assertLess(retarget.angle(animation.local_rotation(decoded[:,24],animation.COMPRESSED),rotations).max(),0.02)

    def test_weapon_swing_and_translation_are_not_frozen_to_the_hand(self):
        F=12
        blob=self.fighter.clip(TR.smooth_values(F))
        original=panm.Animation(blob)
        tracks=[(t.node,t.values(F),panm.RAW,t.flags,t.channel) for t in original.tracks]
        samples=[]
        for f in range(F):
            R=TR.rot_about([0,1,0],f/(F-1)*np.pi/2)
            samples.append(TA.sample(q=TA.matrix_quaternion(R),t=(10+2*f/(F-1),0,0)))
        tracks.append(('Sword',samples,panm.RAW,0x80,'Transform'))
        values,_=self.converter.channels(panm.Animation(TA.clip(tracks,F)))
        R=animation.local_rotation(values[:,24],animation.COMPRESSED)
        self.assertAlmostEqual(float(retarget.angle(R[0],R[-1])),90.,places=4)
        parent=self.target['parent'][-1]
        scale=np.linalg.norm(bone.world_matrices(self.target)[parent,:3,0])
        self.assertAlmostEqual(float(np.linalg.norm(values[-1,23]-values[0,23])*scale),20.,places=4)
        self.assertGreater(np.linalg.norm(R[-1]@np.array([0.,0.,1000.])-R[0]@np.array([0.,0.,1000.])),500.)

    def test_invalid_pair_or_missing_bone_is_rejected(self):
        with self.assertRaises(ValueError):
            anim.Converter(self.source,self.target,weapons=[dict(self.spec,pair=20)])
        with self.assertRaises(KeyError):
            anim.Converter(self.source,self.target,weapons=[dict(self.spec,bone='Absent')])

    def test_scale_is_carried_separately_and_survives_encoding(self):
        F=12
        converter=anim.Converter(self.source,self.target,weapons=[dict(self.spec,scale_pair=10)])
        original=panm.Animation(self.fighter.clip(TR.smooth_values(F)))
        tracks=[(t.node,t.values(F),panm.RAW,t.flags,t.channel) for t in original.tracks]
        samples=[TA.sample(s=(s,s,s),t=(10,0,0)) for s in np.linspace(1,0.001,F)]
        tracks.append(('Sword',samples,panm.RAW,0x80,'Transform'))
        blob=TA.clip(tracks,F)
        encoded=converter.animation(blob)
        decoded=animation.decode(encoded)['values']
        self.assertEqual(decoded.shape,(F,45,3))
        np.testing.assert_allclose(decoded[:,43,0],np.linspace(1,0.001,F),atol=0.002)
        definition=types.SimpleNamespace(NAME='Fixture',CODE='tst',DONOR='lar',SEX='male',TEKKEN8_CODE='test')
        manifest=pack.character_ini(definition,18,weapons=[(0,9,[(0,0)],None,True,10)])
        self.assertIn('weapons = 0:9:0:-1:1:10',manifest)

    def test_scale_channel_cannot_overwrite_another_weapon(self):
        with self.assertRaises(ValueError):
            anim.Converter(self.source,self.target,weapons=[dict(self.spec,scale_pair=0)])
        with self.assertRaises(ValueError):
            anim.Converter(self.source,self.target,weapons=[dict(self.spec,scale_pair=20)])

    def test_combat_grip_uses_its_original_joint_among_role_aliases(self):
        names=['R_Hand', 'R_Hand@R_Have', 'R_Hand@R_Have2']
        self.assertEqual(weapons.source_index(names,'R_Have'),1)
        self.assertEqual(weapons.source_index(names,'R_Have2'),2)
        with self.assertRaises(ValueError):
            weapons.source_index(names+['Other@R_Have'],'R_Have')


if __name__ == '__main__':
    unittest.main()
