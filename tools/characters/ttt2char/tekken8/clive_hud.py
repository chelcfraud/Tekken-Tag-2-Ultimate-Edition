"""The player's original T8 Zantetsuken numeral masks, stored locally only."""
import struct

import numpy as np
from PIL import Image

from .texture import Texture2D

PATH='/Game/UI/Widget/HUD/PowIcon/okm/T_UI_HUD_Pow_okm_Num'
SIZE=128


def encode(rgba):
    if rgba.shape!=(256,1536,4):
        raise ValueError('unexpected Clive number atlas layout')
    masks=[]
    # Cell zero is empty; the five subsequent cells are levels 1..5.
    for level in range(1,6):
        alpha=Image.fromarray(np.asarray(rgba[:,256*level:256*(level+1),3],np.uint8))
        masks.append(alpha.resize((SIZE,SIZE),Image.Resampling.LANCZOS).tobytes())
    return struct.pack('<4sIII',b'ZHUD',1,SIZE,SIZE)+b''.join(masks)


def build(store):
    return encode(Texture2D(store,PATH).decode())
