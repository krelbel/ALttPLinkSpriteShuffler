# ALttPLinkSpriteShuffler

Shuffles all of the head, body, and/or bunny sprites in Link's spritesheet in
any randomizer or ALttP JP 1.0 ROM

**EASY FIRST USAGE**:
`python Main.py --rom sourcerom.sfc --head --zspr_out` which generates
`Spriteshuffled_head_sourcerom.zspr`, a .zspr file with Link's head sprites
shuffled with each other, which can be used on http://alttpr.com by selecting
"Load Custom Sprite", the last entry in the sprite chooser after ROM
generation.

**EASY BUNNY-ONLY USAGE**:
`python Main.py --dumpsprites --rom sourcerom.sfc --multibunny --zspr_out`
to update ./sprites/alttpr/ with the latest sprites from
https://alttpr.com/sprites for use with bunny shuffle or multisprite shuffle
(only need to do this once, takes a while the first time, but re-checking
is fast and the --dumpsprites option isn't required after the first time)
to generate `Spriteshuffled_bunny_sourcerom.zspr`, a .zspr
file with the Link sprite unchanged, but bunny sprite and bunny palette
swapped out for the bunny sprite/palette from a random .zspr file in the
./sprites/ folder.  Can combine this with other sprite shuffle options.

Credit goes to Synack for the idea.

DETAILED OPTIONS:

1) **--rom**: The randomizer or ALttP JP 1.0 ROM containing the source
   spritesheet for the shuffler.

2) **--zspr_in**: The Z Sprite (.zspr) file to use as the source spritesheet
   for the shuffler instead of a ROM.  Forces --zspr_out to be enabled.

3) **--zspr_out**: Instead of generating a patched rom (like
   `Spriteshuffled_head_rom.sfc`), generate a Z Sprite (.zspr) file (like
   `Spriteshuffled_head_rom.zspr`) for use on other .zspr sprite loaders,
   like the http://alttpr.com main site as of v31.0.7.

4) **--head**: Shuffle heads with other heads

5) **--body**: Shuffle bodies with other bodies

6) **--head --body**: Shuffle heads and bodies within their own pools, but
   don't exchange heads with bodies

7) **--chaos**: Shuffle all heads and bodies in the same pool.  Overrides
   --head/--body

8) **--dumpsprites**: Download all the latest sprites from
   https://alttpr.com/sprites into the ./sprites/alttpr/ subfolder; this may
   take a while, but only needs to be done once.  Skips sprites that have
   been downloaded before.  The ./sprites/ folder must contain .zspr files
   for use in all the options below.

9) **--multibunny**: Replace the bunny sprite/palette with a bunny
   sprite/palette from a random .zspr spritesheet in the ./sprites/ folder.
   Bunny heads/bodies aren't scrambled, because you wouldn't want to hurt
   the poor bunny, would you?

10) **--multisprite_simple**: When generating the shuffled spritesheet,
    instead of sourcing exclusively from the sprite in the provided --rom,
    source each head and/or body sprite from the equivalent position within
    a random .zspr spritesheet in the ./sprites/ folder.  Since this loads
    sprites with the palette they weren't designed with, this usually looks
    awful.

11) **--multisprite_full**: Same as --multisprite_simple, except each
    destination sprite 2x2 tile is shuffled from a random 2x2 tile within a
    random .zspr spritesheet.  Combine with --chaos for maximum nonsense.

