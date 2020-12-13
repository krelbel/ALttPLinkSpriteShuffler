# ALttPLinkSpriteShuffler

Sprites in the sprites/ folder pulled from https://alttpr.com/sprites on 7/21 (thanks Fish)

Shuffles all of the head and/or body sprites in Link's spritesheet in any randomizer or ALttP JP 1.0 ROM

Can export a patched ROM or a .zspr file (for use on other .zspr sprite loaders, like
the http://alttpr.com main site as of v31.0.7) with the --zspr argument.

Can shuffle heads only with other heads (--head), bodies with only other bodies (--body),
both heads and bodies but each within their own pool (--head --body), or all head and body
sprites shuffled in the same pool (--chaos).

Can also source randomly from all .zspr sprites in the ./sprites/ subfolder, instead of
sourcing from the spritesheet already present in the provided ROM.  Since this loads
sprites with the palette they weren't designed with, this will certainly look awful.
Use the --multisprite_{simple,full} options if you want a frankensprite.  Simple sources
each destination sprite from the same position in a random spritesheet (ignoring the
position-altering --head/--body/--chaos args), full sources from random positions in
random sprites.  You probably won't be able to tell the difference.  Don't use this.

Sprites are no longer distributed with this script; use the --dumpsprites option to
update ./sprites/alttpr/ with the latest sprites from https://alttpr.com/sprites
for use with the --multisprite options.

Credit goes to Synack for the idea.

Usage: `python Main.py {--head,--body,--chaos,--multisprite_simple,--multisprite_full,--zspr} --rom lttpromtobepatched.sfc #generates {Frankenspriteshuffled,Spriteshuffled}_{head,body,full,chaos}_lttpromtobepatched.sfc`

EASY FIRST USAGE: `python Main.py --head --rom lttpromwithsourcespritesheet.sfc --zspr`
which generates `Spriteshuffled_head_lttpromwithsourcespritesheet.zspr`, a .zspr file with
Link's head sprites shuffled with each other, which can be used on http://alttpr.com by
selecting "Load Custom Sprite" after ROM generation.
 
