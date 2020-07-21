import logging
import argparse
import os
import random

__version__ = '0.1-dev'

#Shuffles all of the head and/or body sprites in Link's spritesheet in the ALttP 1.0 JP ROM.

#Can shuffle heads only with other heads (--head), bodies with only other bodies (--body),
#both heads and bodies but each within their own pool (--head --body), or all head and body
#sprites shuffled in the same pool (--chaos).

#Credit goes to Synack for the idea.

#Usage: python Main.py {--head,--body,--chaos} --rom lttpromtobepatched.sfc #generates Spriteshuffled_{head,body,full,chaos}_lttpromtobepatched.sfc
#General rom patching logic copied from https://github.com/LLCoolDave/ALttPEntranceRandomizer

def write_byte(rom, address, value):
    rom[address] = value

# Tile offsets starting at 0x80000 for all head and body sprites
# These should really be 2D.  Sorry.
head_offsets = [0, 1, 2, 3, 4, 5, 6, 7, 16*1+7, 16*4+2, 16*4+3, 16*4+4, 16*4+7, 16*6+5, 16*6+6, 16*10+3, 16*10+4, 16*10+5, 16*11+5, 16*11+6, 16*11+7, 16*20+0, 16*20+1, 16*20+2, 16*23+1, 16*25+0, 16*25+1, 16*25+3]

body_offsets = [
16*1+0, 16*1+1, 16*1+2, 16*1+3, 16*1+4, 16*1+5, 16*1+6,
16*2+0, 16*2+1, 16*2+2, 16*2+3, 16*2+4, 16*2+5, 16*2+6, 16*2+7,
16*3+0, 16*3+1, 16*3+2, 16*3+3, 16*3+4, 16*3+5, 16*3+6, 16*3+7,
16*4+0, 16*4+1, 16*5+5, 16*5+6, 16*5+7, 16*6+7, 16*8+0, 16*8+1, 16*8+2,
16*11+3, 16*11+4, 
16*12+0, 16*12+1, 16*12+2, 16*12+3, 16*12+4, 16*12+5, 16*12+6, 16*12+7,
16*13+0, 16*13+1, 16*13+2, 16*13+3, 16*13+4, 16*13+5, 16*13+6, 16*13+7,
16*14+0, 16*14+1, 16*14+2, 16*14+3, 16*14+4, 16*14+5, 16*14+6, 16*14+7,
16*15+1, 16*15+2, 16*15+3, 16*15+4, 16*15+5, 16*15+6, 16*15+7,
16*16+0, 16*16+1, 16*16+2, 16*16+3, 16*16+4, 16*16+5, 16*16+6, 16*16+7,
16*17+3, 16*17+4, 16*17+5, 16*17+6, 16*17+7,
16*18+3, 16*18+4, 16*18+5, 16*18+6, 16*18+7,
16*19+3, 16*19+4, 16*19+5, 16*19+6, 16*19+7,
16*20+3, 16*20+4, 16*20+5, 16*20+6, 16*20+7,
16*21+0, 16*21+1, 16*21+2, 16*21+3, 16*21+4, 16*21+5, 16*21+6, 16*21+7,
16*22+0, 16*22+1, 16*22+2, 16*22+3, 16*22+4, 16*22+5, 16*22+6, 16*22+7,
16*23+0, 16*23+2, 16*23+3, 16*23+4, 16*23+5, 16*23+6, 16*23+7,
16*24+0, 16*24+1, 16*24+2, 16*24+3, 16*24+4, 16*24+5, 16*25+4]

def shuffle_sprite(args):
    logger = logging.getLogger('')

    logger.info('Patching ROM.')

    rom = bytearray(open(args.rom, 'rb').read())

    sprite = bytearray(28672)

    for i in range(28672):
        sprite[i] = rom[0x80000+i]

    shuffled_head_offsets = head_offsets.copy()
    random.shuffle(shuffled_head_offsets)

    shuffled_body_offsets = body_offsets.copy()
    random.shuffle(shuffled_body_offsets)

    all_offsets = head_offsets + body_offsets
    shuffled_all_offsets = all_offsets.copy()
    random.shuffle(shuffled_all_offsets)

    height = 2 # All shuffled sprites are 2 tiles high

    if (args.head):
        for off in range(len(head_offsets)):
            for h in range(height):
                srcoff = shuffled_head_offsets[off]*0x40 + h*0x200
                dstoff = 0x80000 + head_offsets[off]*0x40 + h*0x200
                for w in range(0x40):
                    write_byte(rom, dstoff+w, sprite[srcoff+w])

    if (args.body):
        for off in range(len(body_offsets)):
            for h in range(height):
                srcoff = shuffled_body_offsets[off]*0x40 + h*0x200
                dstoff = 0x80000 + body_offsets[off]*0x40 + h*0x200
                for w in range(0x40):
                    write_byte(rom, dstoff+w, sprite[srcoff+w])
    
    if (args.chaos):
        for off in range(len(all_offsets)):
            for h in range(height):
                srcoff = shuffled_all_offsets[off]*0x40 + h*0x200
                dstoff = 0x80000 + all_offsets[off]*0x40 + h*0x200
                for w in range(0x40):
                    write_byte(rom, dstoff+w, sprite[srcoff+w])

    prefix = "Spriteshuffled"
    if (args.chaos):
        prefix += "_chaos"
    elif (args.head and args.body):
        prefix += "_full"
    elif (args.head):
        prefix += "_head"
    elif (args.body):
        prefix += "_body"
    else:
        logger.info('error, no shuffle specified')
        return

    outfilename = '%s_%s' % (prefix, os.path.basename(args.rom))

    with open('%s' % outfilename, 'wb') as outfile:
        outfile.write(rom)

    logger.info('Done.')

    return

def main(args):
    shuffle_sprite(args)
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--loglevel', default='info', const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
    parser.add_argument('--rom', help='Path to a lttp rom to be patched.')
    parser.add_argument('--head', help='Shuffle head sprites among each other.', action='store_true')
    parser.add_argument('--body', help='Shuffle body sprites among each other.', action='store_true')
    parser.add_argument('--chaos', help='Shuffle all head/body sprites among each other. This will look weird.', action='store_true')
    args = parser.parse_args()

    if args.rom is None:
        input('No rom specified. Please run with -h to see help for further information. \nPress Enter to exit.')
        exit(1)
    if ((args.head != True) and (args.body != True) and (args.chaos != True)):
        input('No shuffle specified. Please run with -h to see help for further information. \nPress Enter to exit.')
        exit(1)
    if not os.path.isfile(args.rom):
        input('Could not find valid rom for patching at path %s. Please run with -h to see help for further information. \nPress Enter to exit.' % args.rom)
        exit(1)

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]
    logging.basicConfig(format='%(message)s', level=loglevel)

    main(args)

