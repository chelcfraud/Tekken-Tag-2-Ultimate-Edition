"""Collision diagnostics must expose omitted shapes, schedules and locations."""
import collections
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ttt2char.tekken8 import collision_audit, motbin


class CollisionAudit(unittest.TestCase):
    def test_all_eight_shapes_are_retained_and_losses_are_reported(self):
        shapes = [motbin.Hitbox(10+n, 11+n, 121, 139 if n == 7 else 0, 0,
            100. if n == 6 else 0., 0., (0.,1000.,0.), (0.,0.,0.), 0) for n in range(8)]
        source = types.SimpleNamespace(hitboxes=lambda i: shapes, move_name=lambda i: 'Sword')
        row = dict(first_active=10, last_active=11, hitbox=bytes([70,0,70,0]))
        c = types.SimpleNamespace(k=source, newidx={1: 2}, T={'moves':[{}, {}, row]},
            hit_location=lambda n: {121:70}.get(n,n), stats=collections.Counter({'own moves converted':1}))
        audit = collision_audit.report(c)
        self.assertEqual(audit['status'], 'incomplete')
        move = audit['moves'][0]
        self.assertEqual(len(move['source_hitboxes']), 8)
        self.assertEqual(move['unresolved_locations'], [139])
        self.assertEqual(set(move['review_required']), {'more_than_two_shapes',
            'individual_active_windows', 'explicit_geometry', 'unresolved_locations'})
        self.assertEqual(move['source_hitboxes'][6]['radius'], 100.)
        self.assertEqual(move['source_hitboxes'][7]['last'], 18)

    def test_simple_summary_is_not_claimed_as_in_game_validation(self):
        shape=motbin.Hitbox(10,11,9,0,0,0.,0.,(0.,0.,0.),(0.,0.,0.),0)
        c=types.SimpleNamespace(k=types.SimpleNamespace(hitboxes=lambda i:[shape],move_name=lambda i:'Punch'),
            newidx={0:0},T={'moves':[dict(first_active=10,last_active=11,hitbox=bytes([9,0,0,0]))]},
            hit_location=lambda n:n,stats={})
        audit=collision_audit.report(c)
        self.assertEqual(audit['affected_moves'], {})
        self.assertEqual(audit['status'], 'geometry_review_required')


if __name__ == '__main__':
    unittest.main()
