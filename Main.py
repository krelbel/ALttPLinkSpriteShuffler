import logging
import argparse
import os
import random
from pathlib import Path
from urllib.request import urlopen
import json
from glob import glob
from urllib.parse import urlparse
import shutil
import struct

__version__ = '0.5'

# Shuffles all of the head, body, and/or bunny sprites in Link's spritesheet in
# any randomizer or ALttP JP 1.0 ROM
#
# **EASY FIRST USAGE**:
# `python Main.py --rom sourcerom.sfc --head --zspr_out` which generates
# `Spriteshuffled_head_sourcerom.zspr`, a .zspr file with Link's head sprites
# shuffled with each other, which can be used on http://alttpr.com by selecting
# "Load Custom Sprite", the last entry in the sprite chooser after ROM
# generation.
#
# **EASY BUNNY-ONLY USAGE**:
# `python Main.py --dumpsprites --rom sourcerom.sfc --multibunny --zspr_out`
# to update ./sprites/alttpr/ with the latest sprites from
# https://alttpr.com/sprites for use with bunny shuffle or multisprite shuffle
# (only need to do this once, takes a while the first time, but re-checking
# is fast and the --dumpsprites option isn't required after the first time)
# to generate `Spriteshuffled_bunny_sourcerom.zspr`, a .zspr
# file with the Link sprite unchanged, but bunny sprite and bunny palette
# swapped out for the bunny sprite/palette from a random .zspr file in the
# ./sprites/ folder.  Can combine this with other sprite shuffle options.
#
# Credit goes to Synack for the idea.
#
# DETAILED OPTIONS:
#
# 1) **--rom**: The randomizer or ALttP JP 1.0 ROM containing the source
#    spritesheet for the shuffler.
#
# 2) **--zspr_in**: The Z Sprite (.zspr) file to use as the source spritesheet
#    for the shuffler instead of a ROM.  Forces --zspr_out to be enabled.
#
# 3) **--zspr_out**: Instead of generating a patched rom (like
#    `Spriteshuffled_head_rom.sfc`), generate a Z Sprite (.zspr) file (like
#    `Spriteshuffled_head_rom.zspr`) for use on other .zspr sprite loaders,
#    like the http://alttpr.com main site as of v31.0.7.
#
# 4) **--head**: Shuffle heads with other heads
#
# 5) **--body**: Shuffle bodies with other bodies
#
# 6) **--head --body**: Shuffle heads and bodies within their own pools, but
#    don't exchange heads with bodies
#
# 7) **--chaos**: Shuffle all heads and bodies in the same pool.  Overrides
#    --head/--body
#
# 8) **--dumpsprites**: Download all the latest sprites from
#    https://alttpr.com/sprites into the ./sprites/alttpr/ subfolder; this may
#    take a while, but only needs to be done once.  Skips sprites that have
#    been downloaded before.  The ./sprites/ folder must contain .zspr files
#    for use in all the options below.
#
# 9) **--multibunny**: Replace the bunny sprite/palette with a bunny
#    sprite/palette from a random .zspr spritesheet in the ./sprites/ folder.
#    Bunny heads/bodies aren't scrambled, because you wouldn't want to hurt
#    the poor bunny, would you?
#
# 10) **--multisprite_simple**: When generating the shuffled spritesheet,
#     instead of sourcing exclusively from the sprite in the provided --rom,
#     source each head and/or body sprite from the equivalent position within
#     a random .zspr spritesheet in the ./sprites/ folder.  Since this loads
#     sprites with the palette they weren't designed with, this usually looks
#     awful.
#
# 11) **--multisprite_full**: Same as --multisprite_simple, except each
#     destination sprite 2x2 tile is shuffled from a random 2x2 tile within a
#     random .zspr spritesheet.  Combine with --chaos for maximum nonsense.
#
# 12) **--make_shadow_edge_visible**: Clears body pixels that overlap with the
#     edge of the shadow in up/right/down stand/swordprimed poses, which helps
#     the generated sprite not interfere with glitches and bomb jumps.

# General rom patching logic copied from https://github.com/LLCoolDave/ALttPEntranceRandomizer

def write_byte(array, address, value):
    array[address] = value

# Tile offsets starting at 0x80000 for all head and body sprites
# These should really be 2D.  Sorry.
#
# This does not include unused offsets, since these are used for
# sprites credits text in many spritesheets, and we don't want
# credits text being shuffled into body positions.  That would
# look bad, and heaven forbid a frankensprite looks bad.
# Source of used/unused offsets:
# https://docs.google.com/document/d/11F14QINktk7f3reGsibIQxp2WRP63j6EYdS3svlliQA/edit
UP = 0
RIGHT = 1
DOWN = 2

# Offset: facing dict, used to keep walk cycle with consistent facing
head_offsets = { # Row from spritesheet commented at the end
        0: RIGHT, 1: DOWN, 2: UP, 3: DOWN, 4: DOWN, 5: DOWN, 6: DOWN, 7: DOWN, # A0-7
        16*1+7: DOWN,                                                          # B7
        16*4+2: RIGHT, 16*4+3: DOWN, 16*4+4: UP, 16*4+7: UP,                   # E2, 3, 4, 7
        16*10+3: RIGHT, 16*10+4: RIGHT,                                        # K3, 4
        16*11+5: DOWN, 16*11+6: RIGHT, 16*11+7: UP,                            # L5-7
        16*20+0: DOWN, 16*20+1: RIGHT, 16*20+2: UP,                            # U0-2
        16*23+1: UP,                                                           # X1
        16*25+0: UP, 16*25+2: DOWN, 16*25+3: RIGHT                             # Z0, 2, 3
}

walk_head_offsets = [0, 16*10+3, 16*10+4]

body_offsets = [
16*1+0, 16*1+1, 16*1+2, 16*1+3, 16*1+4, 16*1+5, 16*1+6,                 # B0-6
16*2+0, 16*2+1, 16*2+2, 16*2+3, 16*2+4, 16*2+5, 16*2+6, 16*2+7,         # C0-7
16*3+0, 16*3+1, 16*3+2, 16*3+3, 16*3+4, 16*3+7,                         # D0-4, 7
16*5+5, 16*5+6, 16*5+7,                                                 # F5-7
16*6+7,                                                                 # G7
16*8+0, 16*8+1, 16*8+2,                                                 # I0-2
16*11+3, 16*11+4,                                                       # L3-4
16*12+0, 16*12+1, 16*12+2, 16*12+3, 16*12+4, 16*12+5, 16*12+6, 16*12+7, # M0-7
16*13+0, 16*13+1, 16*13+2, 16*13+3, 16*13+4, 16*13+5, 16*13+6, 16*13+7, # N0-7
16*14+0, 16*14+1, 16*14+2, 16*14+3, 16*14+4, 16*14+5, 16*14+6, 16*14+7, # O0-7
16*15+1, 16*15+2, 16*15+3, 16*15+4, 16*15+5, 16*15+6, 16*15+7,          # P1-7
16*16+0, 16*16+1, 16*16+5, 16*16+6, 16*16+7,                            # Q0-1, 5-7
16*17+6, 16*17+7,                                                       # R6-7
16*18+3, 16*18+4, 16*18+5, 16*18+6, 16*18+7,                            # S3-7
16*19+3, 16*19+4, 16*19+5, 16*19+6, 16*19+7,                            # T3-7
16*20+4, 16*20+5, 16*20+6, 16*20+7,                                     # U4-7
16*21+0, 16*21+1, 16*21+2, 16*21+3, 16*21+4, 16*21+5, 16*21+6,          # V0-6
16*23+2, 16*23+3, 16*23+4, 16*23+5, 16*23+6, 16*23+7,                   # X2-7
16*24+0, 16*24+1, 16*24+2, 16*24+3, 16*24+4, 16*24+5,                   # Y0-5
16*25+4,                                                                # Z4
16*26+7,                                                                # AA7
16*27+0, 16*27+1, 16*27+2, 16*27+3, 16*27+4]                            # AB0-4

bunny_offsets = [
16*25+5, 16*25+7,                                              # Z5, Z7
16*26+0, 16*26+1, 16*26+2, 16*26+3, 16*26+4, 16*26+5, 16*26+6] # AA0-6

def pick_random_zspr(scan_offset, spritelist):
    basespriteoffset = 0
    basepaletteoffset = 0
    srcsheet = []

    if not spritelist:
        logger.info("ERROR: couldn't find sprite for shuffling, make sure you've run --dumpsprites first.")
        return

    # Pick a random sprite, but make sure it has sprite data at the chosen
    # offset first (don't want the shuffled spritesheet to pick from the head
    # region of body-only sprites or vice versa, since that's boring.)
    foundspr = False
    while foundspr is False:
        srcpath = random.choice(spritelist)
        srcsheet = srcpath.read_bytes()
        basespriteoffset = struct.unpack_from('<i', srcsheet, 9)[0]
        basepaletteoffset = struct.unpack_from('<i', srcsheet, 15)[0]
        if (basespriteoffset == 0 or
            basepaletteoffset == 0 or
            basespriteoffset + 0x7000 > basepaletteoffset or
            basespriteoffset + 0x7000 > len(srcsheet) or
            basepaletteoffset + 124 > len(srcsheet)):
            logger.info("WARNING: skipping corrupted sprite " + str(srcpath))
        else:
            for tst_h in range(2):
                srcoff = basespriteoffset + scan_offset*0x40 + tst_h*0x200
                for tst_w in range(0x40):
                    if srcsheet[srcoff + tst_w]:
                        foundspr = True
                        break

    return srcsheet, basespriteoffset, basepaletteoffset

def shuffle_offsets(args, sprite, base_offsets, shuffled_offsets, spritelist, current_sprite):
    for off in range(len(base_offsets)):
        if (args.multisprite_simple or args.multisprite_full):
            if (args.multisprite_simple):
                srcsheet, baseoff, paloff = pick_random_zspr(base_offsets[off], spritelist)
            else:
                srcsheet, baseoff, paloff = pick_random_zspr(shuffled_offsets[off], spritelist)
        else:
            srcsheet = current_sprite
            baseoff = 0

        for h in range(2): # All shuffled sprites are 2x2 tiles
            if (args.multisprite_simple):
                srcoff = baseoff + base_offsets[off]*0x40 + h*0x200
            else:
                srcoff = baseoff + shuffled_offsets[off]*0x40 + h*0x200

            dstoff = base_offsets[off]*0x40 + h*0x200

            for w in range(0x40):
                write_byte(sprite, dstoff+w, srcsheet[srcoff+w])

# .zspr file dumping logic copied with permission from SpriteSomething:
# https://github.com/Artheau/SpriteSomething/blob/master/source/meta/classes/spritelib.py#L443 (thanks miketrethewey!)
def dump_zspr(basesprite, basepalette, baseglove, outfilename):
    palettes = basepalette
    # Add glove data
    palettes.extend(baseglove)
    HEADER_STRING = b"ZSPR"
    VERSION = 0x01
    SPRITE_TYPE = 0x01  # this format has "1" for the player sprite
    RESERVED_BYTES = b'\x00\x00\x00\x00\x00\x00'
    QUAD_BYTE_NULL_CHAR = b'\x00\x00\x00\x00'
    DOUBLE_BYTE_NULL_CHAR = b'\x00\x00'
    SINGLE_BYTE_NULL_CHAR = b'\x00'

    write_buffer = bytearray()

    write_buffer.extend(HEADER_STRING)
    write_buffer.extend(struct.pack('B', VERSION)) # as_u8
    checksum_start = len(write_buffer)
    write_buffer.extend(QUAD_BYTE_NULL_CHAR) # checksum
    sprite_sheet_pointer = len(write_buffer)
    write_buffer.extend(QUAD_BYTE_NULL_CHAR)
    write_buffer.extend(struct.pack('<H', len(basesprite))) # as_u16
    palettes_pointer = len(write_buffer)
    write_buffer.extend(QUAD_BYTE_NULL_CHAR)
    write_buffer.extend(struct.pack('<H', len(palettes))) # as_u16
    write_buffer.extend(struct.pack('<H', SPRITE_TYPE)) # as_u16
    write_buffer.extend(RESERVED_BYTES)
    # sprite.name
    write_buffer.extend(outfilename.encode('utf-16-le'))
    write_buffer.extend(DOUBLE_BYTE_NULL_CHAR)
    # author.name
    write_buffer.extend("ALttPLinkSpriteShuffler".encode('utf-16-le'))
    write_buffer.extend(DOUBLE_BYTE_NULL_CHAR)
    # author.name-short
    write_buffer.extend("SpriteShuffler".encode('ascii'))
    write_buffer.extend(SINGLE_BYTE_NULL_CHAR)
    write_buffer[sprite_sheet_pointer:sprite_sheet_pointer +
                 4] = struct.pack('<L', len(write_buffer)) # as_u32
    write_buffer.extend(basesprite)
    write_buffer[palettes_pointer:palettes_pointer +
                 4] = struct.pack('<L', len(write_buffer)) # as_u32
    write_buffer.extend(palettes)

    checksum = (sum(write_buffer) + 0xFF + 0xFF) % 0x10000
    checksum_complement = 0xFFFF - checksum

    write_buffer[checksum_start:checksum_start +
                 2] = struct.pack('<H', checksum) # as_u16
    write_buffer[checksum_start + 2:checksum_start +
                 4] = struct.pack('<H', checksum_complement) # as_u16

    with open('%s' % outfilename, "wb") as zspr_file:
        zspr_file.write(write_buffer)

def dump_rom(rom, basesprite, basepalette, baseglove, outfilename):
    rom[0x80000:0x87000] = basesprite
    rom[0xdd308:0xdd380] = basepalette
    rom[0xdedf5:0xdedf9] = baseglove
    with open('%s' % outfilename, 'wb') as outfile:
        outfile.write(rom)

def shuffle_link(args, sprite, spritelist):
    logger = logging.getLogger('')

    current_sprite = sprite[:]

    head_offsets_list = list(head_offsets.keys())
    shuffled_head_offsets = head_offsets_list.copy()
    random.shuffle(shuffled_head_offsets)

    # Link's walk cycle uses heads A0, K3, and K4 changing every couple frames;
    # if these are swapped with any random head facing any random direction,
    # the result is usually gibberish.  To make this look a bit nicer, this
    # code picks a random direction, then ensures all 3 frames of Link's
    # left/right head walk cycle are facing the same direction.
    #
    # See https://github.com/krelbel/ALttPLinkSpriteShuffler/issues/1
    nonwalk_head_offsets = [i for i in head_offsets_list if i not in walk_head_offsets]
    random_facing = random.randint(0,2)

    for walk_head_offset in walk_head_offsets:
        off = head_offsets_list.index(walk_head_offset)
        shuffled_pose = shuffled_head_offsets[off]

        if head_offsets[shuffled_pose] != random_facing:
            # Exchange this element in shuffled_head_offsets that will end
            # up at this frame of the walking animation with one facing the
            # consistent direction

            while True:
                swap_pose = random.choice(nonwalk_head_offsets)
                swap_off = head_offsets_list.index(swap_pose)
                shuffled_swap_pose = shuffled_head_offsets[swap_off]
                if head_offsets[shuffled_swap_pose] == random_facing:
                    tmp = shuffled_head_offsets[off]
                    shuffled_head_offsets[off] = shuffled_head_offsets[swap_off]
                    shuffled_head_offsets[swap_off] = tmp
                    break

        shuffled_pose = shuffled_head_offsets[off]

    shuffled_body_offsets = body_offsets.copy()
    random.shuffle(shuffled_body_offsets)

    all_offsets = head_offsets_list + body_offsets
    shuffled_all_offsets = all_offsets.copy()
    random.shuffle(shuffled_all_offsets)

    if (args.head):
        shuffle_offsets(args, sprite, head_offsets_list, shuffled_head_offsets, spritelist, current_sprite)

    if (args.body):
        shuffle_offsets(args, sprite, body_offsets, shuffled_body_offsets, spritelist, current_sprite)
    
    if (args.chaos):
        shuffle_offsets(args, sprite, all_offsets, shuffled_all_offsets, spritelist, current_sprite)

def shuffle_bunny(args, sprite, palette, spritelist):
    logger = logging.getLogger('')

    # Pick a random sprite, but make sure it has a non-transparent bunny sprite
    # first (just checking bunny head Z5 for nonzero pixel data here)
    srcsheet, basespriteoffset, basepaletteoffset = pick_random_zspr(bunny_offsets[0], spritelist)
    
    for off in bunny_offsets:
        for h in range(2): # All bunny sprites consist of 2x2 tiles
            byteoffset = off*0x40 + h*0x200
            srcoff = basespriteoffset + byteoffset
            dstoff = byteoffset
            for w in range(0x40):
                write_byte(sprite, dstoff+w, srcsheet[srcoff+w])

    # Copy bunny palette; palettes are 4 sets of 30 bytes (green, blue, red, bunny) +
    # 4 bytes for gloves, so grab bytes 90-119 of the palette block from the source
    # .zspr file
    dstpaletteoffset = 30*3
    srcpaletteoffset = basepaletteoffset + 30*3
    for b in range(30):
        write_byte(palette, dstpaletteoffset+b, srcsheet[srcpaletteoffset+b])

# Remove body pixels that overlap with the edge of the shadow
def make_shadow_edge_visible(sprite):

    # 4bpp SNES encoding:
    # [r0, bp1], [r0, bp2], [r1, bp1], [r1, bp2], [r2, bp1], [r2, bp2], [r3, bp1], [r3, bp2]
    # [r4, bp1], [r4, bp2], [r5, bp1], [r5, bp2], [r6, bp1], [r6, bp2], [r7, bp1], [r7, bp2]
    # [r0, bp3], [r0, bp4], [r1, bp3], [r1, bp4], [r2, bp3], [r2, bp4], [r3, bp3], [r3, bp4]
    # [r4, bp3], [r4, bp4], [r5, bp3], [r5, bp4], [r6, bp3], [r6, bp4], [r7, bp3], [r7, bp4]
    #
    # Shadow outline pixels for up/down poses:
    #
    #   01234567 01234567
    # 0 00000000 00000000
    # 1 00000000 00000000
    # 2 00000000 00000000
    # 3 00100000 00000100
    # 4 00100000 00000100
    # 5 00011000 00011000
    # 6 00000111 11100000
    # 7 00000000 00000000
    #
    # Masks to clear sprite pixels overlapping these shadow outline pixels
    # (and pixels outside them) in 4bpp:

    left_shadow_updown = [
        0,0,        0,0,        0,0,        0xe0,0xe0,
        0xe0,0xe0,  0xf8,0xf8,  0xff,0xff,  0xff,0xff,
        0,0,        0,0,        0,0,        0xe0,0xe0,
        0xe0,0xe0,  0xf8,0xf8,  0xff,0xff,  0xff,0xff]
    right_shadow_updown = [
        0,0,        0,0,        0,0,        0x7,0x7,
        0x7,0x7,    0x1f,0x1f,  0xff,0xff,  0xff,0xff,
        0,0,        0,0,        0,0,        0x7,0x7,
        0x7,0x7,    0x1f,0x1f,  0xff,0xff,  0xff,0xff]

    # Shadow outline pixels for left/right poses (since the sprite is rendered
    # at a different offset with respect to the shadow compared to up/down
    # sprites, the pixels we remove from the sprite need to be offset as well):
    #
    #   01234567 01234567
    # 0 00000000 00000000
    # 1 00000000 00000000
    # 2 00000000 00000000
    # 3 00000000 00000000
    # 4 00010000 00000010
    # 5 00010000 00000010
    # 6 00001100 00001100
    # 7 00000011 11110000

    left_shadow_right = [
        0,0,        0,0,        0,0,        0,0,
        0xf0,0xf0,  0xf0,0xf0,  0xfc,0xfc,  0xff,0xff,
        0,0,        0,0,        0,0,        0,0,
        0xf0,0xf0,  0xf0,0xf0,  0xfc,0xfc,  0xff,0xff]
    right_shadow_right = [
        0,0,        0,0,        0,0,        0,0,
        0x2,0x2,    0x2,0x2,    0xf,0xf,    0xff,0xff,
        0,0,        0,0,        0,0,        0,0,
        0x2,0x2,    0x2,0x2,    0xf,0xf,    0xff,0xff]

    updown_shadow_offsets = [
        16*1+3,  # B3 stand down
        16*2+1,  # C1 stand up
        16*12+0, # M0 sword primed down
        16*12+3] # M3 sword primed up

    right_shadow_offsets = [
        16*1+0,  # B0 stand right.  this flickers the walk cycle...
        16*12+6] # M6 sword primed right

    for off in updown_shadow_offsets:
        base = off * 0x40 + 0x200 # shadow's in the bottom 2 tiles
        for w in range(32):
            write_byte(sprite, base+w, (sprite[base+w] & (~(left_shadow_updown[w]))))
        for w in range(32):
            write_byte(sprite, base+32+w, (sprite[base+32+w] & (~(right_shadow_updown[w]))))

    for off in right_shadow_offsets:
        base = off * 0x40 + 0x200 # shadow's in the bottom 2 tiles
        for w in range(32):
            write_byte(sprite, base+w, (sprite[base+w] & (~(left_shadow_right[w]))))
        for w in range(32):
            write_byte(sprite, base+32+w, (sprite[base+32+w] & (~(right_shadow_right[w]))))
        

def open_rom(srcfile):
    rom = bytearray(open(srcfile, 'rb').read())
    basesprite = rom[0x80000:0x87000]
    basepalette = rom[0xdd308:0xdd380]
    baseglove = rom[0xdedf5:0xdedf9]
    return rom, basesprite, basepalette, baseglove

def open_zspr(srcfile):
    data = bytearray(open(srcfile, 'rb').read())

    # .zspr import copied with permission from SpriteSomething
    # https://github.com/Artheau/SpriteSomething/blob/master/source/meta/classes/spritelib.py#L131 (thanks miketrethewey!)
    if data[0:4] != bytes(ord(x) for x in 'ZSPR'):
        print("ERROR, invalid .zspr file specified: " + args.zspr_in)
        return
    if data[4] == 1:
        pixel_data_offset = int.from_bytes(
            data[9:13], byteorder='little', signed=False)
        pixel_data_length = int.from_bytes(
            data[13:15], byteorder='little', signed=False)
        palette_data_offset = int.from_bytes(
            data[15:19], byteorder='little', signed=False)
        palette_data_length = int.from_bytes(
            data[19:21], byteorder='little', signed=False)

        if (pixel_data_offset == 0 or
            palette_data_offset == 0 or
            pixel_data_offset + 0x7000 > palette_data_offset or
            pixel_data_offset + 0x7000 > len(data) or
            palette_data_offset + 124 > len(data)):
            print("ERROR, corrupt .zspr file specified: " + args.zspr_in)
            return

        basesprite = data[pixel_data_offset:pixel_data_offset + pixel_data_length]
        basepalette = data[palette_data_offset:palette_data_offset + palette_data_length - 4]
        baseglove = data[palette_data_offset + palette_data_length - 4:palette_data_offset + palette_data_length]
        return basesprite, basepalette, baseglove
    else:
        print("ERROR, no support for ZSPR version" + str(int(data[4])))

def shuffle_sprite(args):
    logger = logging.getLogger('')

    if (args.multisprite_simple or args.multisprite_full):
        prefix = "Frankenspriteshuffled"
    else:
        prefix = "Spriteshuffled"

    if (args.chaos):
        prefix += "_chaos"
    elif (args.head and args.body):
        prefix += "_full"
    elif (args.head):
        prefix += "_head"
    elif (args.body):
        prefix += "_body"
    elif not args.multibunny:
        logger.info('error, no shuffle specified')
        return

    if (args.multibunny):
        prefix += "_bunny"

    if (args.zspr_out):
        if (args.zspr_in):
            origzsprname = os.path.basename(args.zspr_in)
            shortname = os.path.splitext(origzsprname)[0]
        else:
            origromname = os.path.basename(args.rom)
            shortname = os.path.splitext(origromname)[0]
        outfilename = '%s_%s.zspr' % (prefix, shortname)

        logger.info("Creating .zspr file: " + outfilename)
    else:
        outfilename = '%s_%s' % (prefix, os.path.basename(args.rom))

        logger.info("Creating patched ROM: " + outfilename)

    if args.zspr_in:
        basesprite, basepalette, baseglove = open_zspr(args.zspr_in)
    elif args.rom:
        rom, basesprite, basepalette, baseglove = open_rom(args.rom)

    spritelist = list()
    if (args.multisprite_simple or args.multisprite_full or args.multibunny):
        for path in Path('./sprites/').rglob('*.zspr'):
            spritelist.append(path)

    shuffle_link(args, basesprite, spritelist)

    if (args.multibunny):
        shuffle_bunny(args, basesprite, basepalette, spritelist)

    if (args.make_shadow_edge_visible):
        make_shadow_edge_visible(basesprite)

    if (args.zspr_out):
        dump_zspr(basesprite, basepalette, baseglove, outfilename)
    else:
        dump_rom(rom, basesprite, basepalette, baseglove, outfilename)

# Sprite dumping logic copied from
# https://github.com/Berserker66/MultiWorld-Utilities/blob/doors/source/classes/SpriteSelector.py
def dump_sprites(args):
    logger = logging.getLogger('')
    alttpr_sprite_dir = "./sprites/alttpr"
    successful = True

    if not os.path.isdir(alttpr_sprite_dir):
        os.makedirs(alttpr_sprite_dir)

    try:
        logger.info("Downloading alttpr sprites list")
        with urlopen('https://alttpr.com/sprites') as response:
            sprites_arr = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        logger.info("Error getting list of alttpr sprites. Sprites not updated.\n\n%s: %s" % (type(e).__name__, e))
        successful = False
        return
 
    try:
        logger.info("Determining needed sprites")
        current_sprites = [os.path.basename(file) for file in glob(os.path.join(alttpr_sprite_dir,"*"))]
        alttpr_sprites = [(sprite['file'], os.path.basename(urlparse(sprite['file']).path)) for sprite in sprites_arr]
        needed_sprites = [(sprite_url, filename) for (sprite_url, filename) in alttpr_sprites if filename not in current_sprites]
 
        alttpr_filenames = [filename for (_, filename) in alttpr_sprites]
        obsolete_sprites = [sprite for sprite in current_sprites if sprite not in alttpr_filenames]
    except Exception as e:
        logger.info("Error Determining which sprites to update. Sprites not updated.\n\n%s: %s" % (type(e).__name__, e))
        successful = False
        return
 
    updated = 0
    for (sprite_url, filename) in needed_sprites:
        try:
            logger.info("Downloading needed sprite %g/%g" % (updated + 1, len(needed_sprites)))
            target = os.path.join(alttpr_sprite_dir, filename)
            with urlopen(sprite_url) as response, open(target, 'wb') as out:
                shutil.copyfileobj(response, out)
        except Exception as e:
            logger.info("Error downloading sprite. Not all sprites updated.\n\n%s: %s" % (type(e).__name__, e))
            successful = False
        updated += 1
 
    deleted = 0
    for sprite in obsolete_sprites:
        try:
            logger.info("Removing obsolete sprite %g/%g" % (deleted + 1, len(obsolete_sprites)))
            os.remove(os.path.join(self.alttpr_sprite_dir, sprite))
        except Exception as e:
            logger.info("Error removing obsolete sprite. Not all sprites updated.\n\n%s: %s" % (type(e).__name__, e))
            successful = False
        deleted += 1

    if successful:
        resultmessage = "alttpr sprites updated successfully"

    return

def main(args):
    if args.dumpsprites:
        dump_sprites(args)

    shuffle_sprite(args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--loglevel', default='info', const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
    parser.add_argument('--rom', help='Path to a lttp rom to use as the base spritesheet.')
    parser.add_argument('--zspr_in', help='Path to a .zspr to use as the base spritesheet instead of a rom.')
    parser.add_argument('--zspr_out', help='Output a .zspr instead of a patched rom, convenient for use in other sprite loaders (like the one on alttpr.com).  Automatically true if the base spritesheet is a .zspr file instead of a rom.', action='store_true')
    parser.add_argument('--head', help='Shuffle head sprites among each other.', action='store_true')
    parser.add_argument('--body', help='Shuffle body sprites among each other.', action='store_true')
    parser.add_argument('--chaos', help='Shuffle all head/body sprites among each other. This will look weird.', action='store_true')
    parser.add_argument('--dumpsprites', help='Update ./sprites/alttpr/ with the latest sprites from https://alttpr.com/sprites for use with the --multisprite options.', action='store_true')
    parser.add_argument('--multibunny', help='Pick a random bunny sprite from all bunny sprites in ./sprites/ instead of the bunny sprite in the base spritesheet.', action='store_true')
    parser.add_argument('--multisprite_simple', help='Choose each sprite randomly from all spritesheets in ./sprites/ as sources, instead of the current spritesheet in the provided rom. Keep poses unshuffled (i.e. each sprite will be sourced from the same position in a random sprite).', action='store_true')
    parser.add_argument('--multisprite_full', help='Choose each sprite randomly from all spritesheets in ./sprites/ as sources, instead of the current spritesheet in the provided rom. Shuffle poses according to other args (i.e. each sprite will be sourced from a random position in a random spritesheet according to the other --head/--body/--chaos arguments).', action='store_true')
    parser.add_argument('--make_shadow_edge_visible', help='Clear body pixels that overlap with the edge of the shadow in up/right/down stand/swordprimed poses, which helps the generated sprite not interfere with glitches/bombjumps', action='store_true')
    args = parser.parse_args()

    if not args.dumpsprites:
        if args.rom and args.zspr_in:
            input('Both rom and .zspr source specified, please choose one or the other. Run with -h to see help for further information. \nPress Enter to exit.')
            exit(1)
        if args.rom is None and args.zspr_in is None:
            input('No rom or .zspr source specified. Please run with -h to see help for further information. \nPress Enter to exit.')
            exit(1)
        if ((args.head != True) and (args.body != True) and (args.chaos != True) and (args.multibunny != True)):
            input('No shuffle specified. Please run with -h to see help for further information. \nPress Enter to exit.')
            exit(1)
        if args.rom and not os.path.isfile(args.rom):
            input('Could not find valid rom for patching at path %s. Please run with -h to see help for further information. \nPress Enter to exit.' % args.rom)
            exit(1)
        if args.zspr_in and not os.path.isfile(args.zspr_in):
            input('Could not find valid source zspr at path %s. Please run with -h to see help for further information. \nPress Enter to exit.' % args.rom)
            exit(1)

    if args.zspr_in:
        args.zspr_out = True

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]
    logging.basicConfig(format='%(message)s', level=loglevel)

    main(args)

