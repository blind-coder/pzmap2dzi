from PIL import Image, ImageDraw, ImageFont

import os

from pzmap2dzi import cell, texture, util, mp, pzdzi

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

@lru_cache(maxsize=16)

def load_cell(path, cx, cy):
    return cell.load_cell(path, cx, cy)

def render_square(tl, im, ox, oy, path, sx, sy, layer):
    cx, subx = divmod(sx, 300)
    cy, suby = divmod(sy, 300)
    bx, x = divmod(subx, 10)
    by, y = divmod(suby, 10)
    data = load_cell(path, cx, cy)
    if not data: # Cell doesn't exist
        return False
    block = data['blocks'][bx * 30 + by]
    ldata = block[layer]
    update = False
    if ldata:
        row = ldata[x]
        if row:
            sqr = row[y]
            if sqr:
                for t in sqr['tiles']:
                    tiles = data['header']['tiles']
                    tex = tl.get_by_name(tiles[t], sx, sy)
                    if tex:
                        tex.render(im, ox, oy)
                        update = True
                    else:
                        print('missing tile at {}x{} (cell {}x{} subtile {}x{}): {}'.format(sx, sy, cx, cy, subx, suby, tiles[t]))
    return update

def render_tile(dzi, tx, ty, tl, in_path, out_path, save_empty, output_format, dry_run):
    # Get the path for the WIP flag and set it
    flag_path = os.path.join(out_path, 'layer0_files', str(dzi.base_level))
    util.set_wip(flag_path, tx, ty)

    # Iterate through all layers
    for layer in range(dzi.layers):
        gx0, gy0 = dzi.tile2grid(tx, ty, layer)
        left, right, top, bottom = dzi.tile_grid_bound(tx, ty, layer)

        # Create a new image canvas of tile_size^2 size
        im = Image.new('RGBA', (dzi.tile_size, dzi.tile_size))

        # Iterate top-down left-right and render the tiles on the square
        for gy in range(top, bottom + 1):
            for gx in range(left, right + 1):
                # ???
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) // 2
                sy = (gy - gx) // 2
                ox, oy = pzdzi.get_offset_in_tile(gx - gx0, gy - gy0)
                render_square(tl, im, ox, oy, in_path, sx, sy, layer)
        im = dzi.crop_tile(im, tx, ty)

        # Output path where the image will be stored
        layer_output = os.path.join(out_path, 'layer{}_files'.format(layer), str(dzi.base_level))
        if im.getbbox():
            # Save the image
            if not dry_run:
                im.save(os.path.join(layer_output, '{}_{}.{}'.format(tx, ty, output_format)))
        elif layer == 0 and save_empty:
            # Save an empty file, only if requested
            util.set_empty(layer_output, tx, ty)
    util.clear_wip(flag_path, tx, ty)
    return True

def base_work(conf, tiles):
    dzi, tl, in_path, out_path, save_empty, output_format, dry_run = conf
    for tx, ty in tiles:
        render_tile(dzi, tx, ty, tl, in_path, out_path, save_empty, output_format, dry_run)

def process(args):
    # Load textures from extracted packs
    texture_lib = texture.TextureLibrary(args.texture)

    # Setup plants according to parameters
    texture_lib.config_plants(args.season, args.snow, args.flower, args.large_bush,
                              args.tree_size, args.jumbo_tree_size, args.jumbo_tree_type)

    # Create output directory
    util.ensure_folder(args.output)

    if args.verbose:
        print('processing base level:')

    # Initialize DeepZoom Image pyramid
    # params: inputdirectory, tilesize in px, layers to process (1..8), jumbo tree siz
    dzi = pzdzi.DZI(args.input, args.tile_size, args.layers, args.jumbo_tree_size > 3)

    # create DZI directories
    dzi.ensure_folders(args.output)

    # save xml file
    dzi.save_dzi(args.output, None, args.output_format)

    # create path for layer 0
    layer0_path = os.path.join(args.output, 'layer0_files', str(dzi.base_level))

    # ???
    groups = dzi.get_tile_groups(layer0_path, args.group_size)

    # configuration for the multithread runner
    conf = (dzi, texture_lib, args.input, args.output, args.save_empty_tile, args.output_format, args.dry_run)

    # finally, create the floor level
    t = mp.Task(base_work, conf, args.mp)
    if not t.run(groups, args.verbose, args.stop_key):
        return False

    if args.verbose:
        print('base done')

    # No pyramid on dry runs
    if args.dry_run:
        return True

    # create the pyramid from base layers
    for layer in range(dzi.layers):
        if args.verbose:
            print('processing layer {} pyramid:'.format(layer))
        path = os.path.join(args.output, 'layer{}_files'.format(layer))
        if not dzi.merge_all_levels(path, args.mp, args.verbose, args.stop_key, args.output_format):
            return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PZ map base render')
    parser.add_argument('-o', '--output', type=str, default='./output/base')
    parser.add_argument('-t', '--texture', type=str, default='./textures')
    parser.add_argument('-m', '--mp', type=int, default=1)
    parser.add_argument('--season', type=str, default='summer',
                        choices=['spring', 'summer', 'summer2', 'autumn', 'winter'])
    parser.add_argument('--snow', action='store_true')
    parser.add_argument('--large-bush', action='store_true')
    parser.add_argument('--flower', action='store_true')
    parser.add_argument('--tree-size', type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument('--jumbo-tree-size', type=int, default=4, choices=[0, 1, 2, 3, 4, 5])
    parser.add_argument('--jumbo-tree-type', type=int, default=0)
    parser.add_argument('--tile-size', type=int, default=1024)
    parser.add_argument('--layers', type=int, default=8)
    parser.add_argument('--group-size', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-e', '--save-empty-tile', action='store_true')
    parser.add_argument('-s', '--stop-key', type=str, default='')
    parser.add_argument('--output-format', type=str, default='png')
    parser.add_argument('-n', '--dry-run', action='store_true')
    parser.add_argument('input', type=str)
    args = parser.parse_args()

    process(args)
