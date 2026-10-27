"""Clive Rosfield from the player's Tekken 8 installation.

The model, sword, voices and moves are read locally, as for Reina and Noctis.
No donor moveset fallback is permitted for this character.
"""
NAME = 'Clive Rosfield'
SHORT_NAME = 'CLIVE'
TEKKEN8_ID = 36
TEKKEN8_CODE = 'okm'
CODE = 'clv'
SEX = 'male'
DONOR = 'lar'
DONOR_ROW = 38
MOVESET_SOURCE = 'tekken8'
REQUIRE_OWN_MOVESET = True
EXPERIMENTAL = True
EXPERIMENTAL_WARNING = ('Experimental: does not work properly. Character and sword hitboxes use full geometry; '
                        'special moves and Eikon effects remain incomplete.')
COLLISION_AUDIT = True
FULL_HITBOXES = True
REVISION = 6

_MODEL = '/Game/Character/Item/model/unique/okm'
TEKKEN8 = {
    'costume': '1p', 'costume_2p': '2p',
    # The weapon mesh is imported separately so its joints stay animated.
    'parts': [
        ('fac', _MODEL + '/face/okm_fac/meshes/SK_CH_okm_fac'),
        ('har', _MODEL + '/hair/okm_har_1p/meshes/SK_CH_okm_har_1p_msl'),
        ('bdf', _MODEL + '/full_body/okm_bdf_1p/meshes/SK_CH_okm_bdf_1p_msl'),
        ('fah', _MODEL + '/face_hair/okm_fah_1p/meshes/SK_CH_okm_fah_1p_msl'),
    ],
    'merge_order': ['fac', 'bdf', 'har', 'fah'],
}
MESHES = {'bdf': ('clv_bdf_1p', 'KOSHI_jnt', 0), 'fac': ('clv_fac', 'ATAMA_Joint', 2),
          'har': ('clv_har_1p', 'ATAMA_jnt_assist', 3), 'fah': ('clv_fah_1p', 'ATAMA_Joint', 4)}
MATERIALS = {'MI_CH_okm_add_tealine': None, 'MI_CH_okm_eye_ao': None, 'MI_Cal_Mesh': None}

# As for Noctis, these are TTT2 material templates, never replacement textures.
TEMPLATES = {
    'skin': ('jun.nud', 'ude_A_O_OBJ', 0), 'mouth': ('jun.nud', 'cha:kao_O_OBJ', 0),
    'eye': ('jun.nud', 'cha:kao_O_OBJ', 2), 'overlay': ('jun.nud', 'cha:kao_O_OBJ', 7),
    'cloth': (0xD4F28D09, 'jun_upb_1p_b', 0), 'hair': (0x5F412CA4, 'jun_hed_1p', 1),
    'colour': (0xD4F28D09, 'jun_upb_1p_b', 2), 'colour_alpha': (0xD4F28D09, 'jun_upb_1p_b', 1),
}
TEMPLATE_TEXTURES = ['jun.nut', 0x24F8AE59, 0x277C7A37, 0xAD9B60F0, 0x900FD8C4]
_UI = '/Game/UI/Rep_Texture'
ART = {
    'bust': (_UI + '/Makuai_Character_L/T_UI_Makuai_Character_L_okm', (899, 1237, 411)),
    'body': (_UI + '_Other/ST01_Arena/Character_Full/T_okm_1p_C', (750, 207, 100)),
    'name': _UI + '/HUD_Character_Name/T_UI_HUD_Character_Name_okm',
    'costume': _UI + '/CS_Slot_Thumb/okm/T_UI_CS_Character_Slot_okm_1p',
}
VOICE = 'okm'
MOVESET = {
    'name': '[CLIVE]', 'drop_moves': r'^Okm_Direct$',
    'zantetsuken': True,
    # df+2 starts with a grounded stagger, then its second strike launches.
    # The inferred remap to sDw_UP_00_ launches before the sword comes back.
    'source_ground_reactions': ('Okm_t_srpF',),
    'direct': [(r'^La_KAM$', 'move', ['Okm_sKAM00_']),
               (r'^(la|mk)_s', 'anim', ['okm_s%02d' % i for i in range(3)]),
               (r'^la_w', 'anim', ['okm_w%02d' % i for i in range(3)])],
}

_SWORD = _MODEL + '/extra/okm_exp_1p/meshes/SK_CH_okm_exp_1p'
WEAPONS = [
    {'mesh': _SWORD, 'bone': 'ATH_swordR_1st', 'parent': 'TE_R_jnt', 'source_parent': 'R_Hand', 'pair': 0},
    {'mesh': _SWORD, 'bone': 'ATH_swordR_2nd', 'parent': 'TE_R_jnt', 'source_parent': 'R_Hand', 'pair': 1},
    {'mesh': _SWORD, 'bone': 'ATH_saya_2nd', 'parent': 'MUNE2_jnt', 'source_parent': 'Spine2', 'pair': 2},
    {'mesh': _SWORD, 'bone': 'ATH_sword_back', 'parent': 'MUNE2_jnt', 'source_parent': 'Spine2', 'pair': 3},
    # Combat locations are the native R_Have/L_Have/R_Have2 frames.
    # The similarly numbered Weapon_Position asset controls visual traces;
    # its sword-tip/Eikon bones are NOT the combat-location mapping.
    # FULL_HITBOXES applies each hitbox's local offsets in these combat frames.
    {'bone': 'R_Have', 'parent': 'TE_R_jnt', 'source_parent': 'R_Hand', 'pair': 4,
     'points': {121: ('R_Have', 0)}},
    {'bone': 'L_Have', 'parent': 'TE_L_jnt', 'source_parent': 'L_Hand', 'pair': 5,
     'points': {120: ('L_Have', 1)}},
    {'bone': 'R_Have2', 'parent': 'TE_R_jnt', 'source_parent': 'R_Hand', 'pair': 6,
     'points': {127: ('R_Have2', 2)}},
]
VERTEX_BUDGET = 70000

# Extra translation channels carry scale independently of the native rotation
# channels. This preserves the sword's hide/show and blade-tip transformations.
for _weapon in WEAPONS:
    _weapon['scale_pair'] = 10 + _weapon['pair']
del _weapon
