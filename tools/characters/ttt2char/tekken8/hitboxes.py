"""Full T8 attack shapes, evaluated against the native TTT2 hurt capsules.

Offsets are in the source joint frame, including when radius is zero. Weapon
frames are distinct from visual trace bones. The runtime consumes the compact
sidecar; a CRC binds it to the final (including face-retargeted) moveset.
"""
import struct
import zlib

import numpy as np

from .. import InputError
from ..ttt2 import bone
from .anim import DRIVERS

MAGIC = b'T8HB'
VERSION = 1
ENDPOINT = struct.Struct('<5I6f')
SHAPE = struct.Struct('<IIff')
BODY = {4:'Neck', 5:'Head', 6:'R_Shoulder', 7:'R_UpperArm', 8:'R_LowerArm', 9:'R_Hand',
        10:'L_Shoulder', 11:'L_UpperArm', 12:'L_LowerArm', 13:'L_Hand',
        14:'R_UpperLeg', 15:'R_LowerLeg', 16:'R_Foot', 17:'L_UpperLeg', 18:'L_LowerLeg', 19:'L_Foot'}
MIDPOINTS = {138:(7,8), 139:(11,12), 140:(14,15), 141:(17,18)}
GRIPS = {120:'L_Have', 121:'R_Have', 126:'L_Have2', 127:'R_Have2'}


class Endpoints:
    def __init__(self, converter, animation_converter, target):
        self.c, self.a = converter, animation_converter
        self.names = [n.removeprefix('cha:') for n in target['names']]
        self.world = bone.world_matrices(target)
        self.drivers = {source:target for target,source in DRIVERS.items()}

    def body(self, code, offset):
        name = self.drivers[BODY[code]]
        index = self.names.index(name)
        scale = np.linalg.norm(self.world[index,:3,0])
        local = self.a.cal.offsets[name].T @ np.asarray(offset) / scale
        return index, local

    def native(self, code):
        value = self.c.hit_location(code)
        if not 0 <= value <= 77:
            raise InputError('no native collision point for Tekken 8 location %d' % code)
        return value

    def endpoint(self, code, offset):
        offset = np.asarray(offset, np.float64)
        zero = np.zeros(3)
        # kind, point/pair A, point B, body bone A, body bone B, offsets A/B
        if code in GRIPS:
            name = GRIPS[code]
            w = next((w for w in self.a.weapons if self.a.sk.names[w['joint']] == name), None)
            if w is None:
                raise InputError('missing combat grip %s' % name)
            local = w['rotation'].T @ offset / w['parent_scale']
            return (2,w['pair'],0,0,0,*local,*zero)
        if code in MIDPOINTS:
            left,right = MIDPOINTS[code]
            b1,o1 = self.body(left,offset)
            b2,o2 = self.body(right,offset)
            return (3,self.native(left),self.native(right),b1,b2,*o1,*o2)
        if code == 125:
            return (4,0,0,self.names.index('HARA_ROT1'),0,*offset,*zero)
        if np.any(offset) and code in BODY:
            index,local = self.body(code,offset)
            return (1,self.native(code),0,index,0,*local,*zero)
        # Cached body points (26 onward) already contain their anatomical
        # offset in T8's resolver and ignore the extra offset argument.
        if np.any(offset) and code < 26:
            raise InputError('unhandled local collision offset at location %d' % code)
        return (0,self.native(code),0,0,0,*zero,*zero)


def build(c, animation_converter, target):
    """Export all converted attack shapes, including native tag-assault twins.

    Widen only the native eligibility window; individual shape windows remain
    exact in the sidecar. Native guards/damage/hit latches remain in charge.
    """
    endpoints = Endpoints(c,animation_converter,target)
    by_index = {}
    for source,index in sorted(c.newidx.items()):
        shapes = []
        for h in c.k.hitboxes(source):
            if not (h.first or h.last):
                continue
            if h.first > h.last or not np.isfinite([h.radius,h.height,*h.a,*h.b]).all():
                raise InputError('invalid collision shape in move %d' % source)
            shapes.append((h.first,h.last,h.radius,h.height,
                           endpoints.endpoint(h.loc,h.a),
                           endpoints.endpoint(h.loc2,h.b) if h.loc2 else None))
        if shapes:
            by_index[index] = shapes
    for twin,original in getattr(c,'collision_twins',{}).items():
        if original in by_index:
            by_index[twin] = by_index[original]
    entries = []
    for index,row in enumerate(c.T['moves']):
        shapes = by_index.get(index)
        if shapes is None:
            continue
        first,last = min(h[0] for h in shapes),max(h[1] for h in shapes)
        row['first_active'],row['last_active'] = first,last
        row['hitbox'] = bytes(x if x <= 77 else 9 for x in row['hitbox'])
        if not any(row['hitbox']):
            row['hitbox'] = bytes([9,0,9,0])
        global_id = row['move_id_hi'] << 16 | row['move_id_lo']
        entries.append((global_id,shapes))
    out = bytearray(struct.pack('<4sIII',MAGIC,VERSION,0,len(entries)))
    for key,shapes in entries:
        out += struct.pack('<II',key,len(shapes))
        for first,last,radius,height,a,b in shapes:
            out += SHAPE.pack(first,last,radius,height)
            out += ENDPOINT.pack(*a)
            # Kind 5 means a swept sphere, previous point -> current point.
            out += ENDPOINT.pack(*(b if b is not None else (5,0,0,0,0,0.,0.,0.,0.,0.,0.)))
    return bytes(out)


def bind(data, moveset):
    out = bytearray(data)
    struct.pack_into('<I',out,8,zlib.crc32(moveset))
    return bytes(out)
