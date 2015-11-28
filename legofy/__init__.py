from __future__ import unicode_literals

from PIL import Image, ImageSequence
import sys
import os

from math import sqrt
import collections
# Python 2 and 3 support
# TODO: Proper images2gif version that supports both Py 2 and Py 3 (mostly handling binary data)
if sys.version_info < (3,):
    import legofy.images2gif_py2 as images2gif
else:
    import legofy.images2gif_py3 as images2gif


'''http://www.brickjournal.com/files/PDFs/2010LEGOcolorpalette.pdf'''
PALETTE_SOLID = {
    "024 bright_yellow": [0xfe, 0xc4, 0x01],
    "106 bright_orange": [0xe7, 0x64, 0x19],
    "021 bright_red": [0xde, 0x01, 0x0e],
    "221 bright_purple": [0xde, 0x38, 0x8b],
    "023 bright_blue": [0x01, 0x58, 0xa8],
    "028 dark_green": [0x01, 0x7c, 0x29],
    "119 bright_yellowish_green": [0x95, 0xb9, 0x0c],
    "192 reddish_brown": [0x5c, 0x1d, 0x0d],
    "018 nougat": [0xd6, 0x73, 0x41],
    "001 white": [0xf4, 0xf4, 0xf4],
    "026 black": [0x02, 0x02, 0x02],
    "226 cool_yellow": [0xff, 0xff, 0x99],
    "222 light_purple": [0xee, 0x9d, 0xc3],
    "212 light_royal_blue": [0x87, 0xc0, 0xea],
    "037 bright_green": [0x01, 0x96, 0x25],
    "005 brick_yellow": [0xd9, 0xbb, 0x7c],
    "283 light_nougat": [0xf5, 0xc1, 0x89],
    "208 light_stone_grey": [0xe4, 0xe4, 0xda],
    "191 flame_yellowish_orange": [0xf4, 0x9b, 0x01],
    "124 bright_reddish_violet": [0x9c, 0x01, 0xc6],
    "102 medium_blue": [0x48, 0x8c, 0xc6],
    "135 sand_blue": [0x5f, 0x75, 0x8c],
    "151 sand_green": [0x60, 0x82, 0x66],
    "138 sandy_yellow": [0x8d, 0x75, 0x53],
    "038 dark_orange": [0xa8, 0x3e, 0x16],
    "194 medium_stone_grey": [0x9c, 0x92, 0x91],
    "154 dark_red": [0x80, 0x09, 0x1c],
    "268 medium_lilac": [0x2d, 0x16, 0x78],
    "140 earth_blue": [0x01, 0x26, 0x42],
    "141 earth_green": [0x01, 0x35, 0x17],
    "312 medium_nougat": [0xaa, 0x7e, 0x56],
    "199 dark_stone_grey": [0x4d, 0x5e, 0x57],
    "308 dark_brown": [0x31, 0x10, 0x07]
}

PALETTE_TRANSPARENT = {
    "044": [0xf9, 0xef, 0x69],
    "182": [0xec, 0x76, 0x0e],
    "047": [0xe7, 0x66, 0x48],
    "041": [0xe0, 0x2a, 0x29],
    "113": [0xee, 0x9d, 0xc3],
    "126": [0x9c, 0x95, 0xc7],
    "042": [0xb6, 0xe0, 0xea],
    "043": [0x50, 0xb1, 0xe8],
    "143": [0xce, 0xe3, 0xf6],
    "048": [0x63, 0xb2, 0x6e],
    "311": [0x99, 0xff, 0x66],
    "049": [0xf1, 0xed, 0x5b],
    "111": [0xa6, 0x91, 0x82],
    "040": [0xee, 0xee, 0xee]
}

PALETTE_EFFECTS = {
    "131": [0x8d, 0x94, 0x96],
    "297": [0xaa, 0x7f, 0x2e],
    "148": [0x49, 0x3f, 0x3b],
    "294": [0xfe, 0xfc, 0xd5]
}

PALETTE_MONO = {
    "001": [0xf4, 0xf4, 0xf4],
    "026": [0x02, 0x02, 0x02]
}

#private methods

reverse_palette_solid = {tuple(v):k for k,v in PALETTE_SOLID.items()}

color_map = collections.defaultdict()

def rgb_to_yuv(rgb_color):
    w_r = 0.299
    w_b = 0.114
    w_g = 0.587
    u_max = 0.436
    v_max = 0.615
    y_prime = w_r * rgb_color[0] + w_g * rgb_color[1] + w_b * rgb_color[2]
    u = u_max * (rgb_color[2] - y_prime) / (1 - w_b)
    v = v_max * (rgb_color[0] - y_prime) / (1 - w_r)

    return (y_prime, u, v)

def distance_between_colors(real_color, palette_color):
    # euclidean dist
    dist = sqrt(pow((real_color[0] - palette_color[0]), 2) + 
        pow((real_color[1] - palette_color[1]), 2) + 
        pow((real_color[2] - palette_color[2]), 2))
    # YUV
    
    real_yuv = rgb_to_yuv(real_color)
    palette_yuv = rgb_to_yuv(palette_color)
    dist = sqrt(pow((real_yuv[0] - palette_yuv[0]), 2) + 
        pow((real_yuv[1] - palette_yuv[1]), 2) + 
        pow((real_yuv[2] - palette_yuv[2]), 2))

    # CIE

    return dist

def nearest_neighbor_for_real_color(real_color):
    nearest_dist = sys.float_info.max
    nearest_neighbor = None
    for palette_color in PALETTE_SOLID.values():
        dist = distance_between_colors(real_color, tuple(palette_color))
        if dist < nearest_dist:
            nearest_neighbor = tuple(palette_color)
            nearest_dist = dist

    return nearest_neighbor


#end private methods

def iter_frames(image_to_iter):
    '''Function that iterates over the gif's frames'''
    try:
        i = 0
        while 1:
            image_to_iter.seek(i)
            imframe = image_to_iter.copy()
            if i == 0:
                palette = imframe.getpalette()
            else:
                imframe.putpalette(palette)
            yield imframe
            i += 1
    except EOFError:
        pass


def apply_color_overlay(image, color, position=None):
    '''Small function to apply an effect over an entire image'''

    color = nearest_neighbor_for_real_color(color)

    if color in color_map:
        color_map[color] += 1
    else:
        color_map[color] = 1 

    # log position to color map
    # if position:
    #     if reverse_palette_solid[color] == "208 light_stone_grey":
    #         print position

    overlay_red, overlay_green, overlay_blue = color

    channels = image.split()

    r = channels[0].point(lambda color: overlay_effect(color, overlay_red))
    g = channels[1].point(lambda color: overlay_effect(color, overlay_green))
    b = channels[2].point(lambda color: overlay_effect(color, overlay_blue))


    channels[0].paste(r)
    channels[1].paste(g)
    channels[2].paste(b)

    return Image.merge(image.mode, channels)

def overlay_effect(color, overlay):
    '''Actual overlay effect function'''
    if color < 33:
        return overlay - 100
    elif color > 233:
        return overlay + 100
    else:
        return overlay - 133 + color

def make_lego_image(thumbnail_image, brick_image):
    '''Create a lego version of an image from an image'''
    base_width, base_height = thumbnail_image.size
    brick_width, brick_height = brick_image.size

    rgb_image = thumbnail_image.convert('RGB')

    lego_image = Image.new("RGB", (base_width * brick_width,
                                   base_height * brick_height), "white")

    for brick_x in range(base_width):
        for brick_y in range(base_height):
            color = rgb_image.getpixel((brick_x, brick_y))
            lego_image.paste(apply_color_overlay(brick_image, color, (brick_x, brick_y)),
                             (brick_x * brick_width, brick_y * brick_height))
    return lego_image


def get_new_filename(file_path, ext_override=None):
    '''Returns the save destination file path'''
    folder, basename = os.path.split(file_path)
    base, extention = os.path.splitext(basename)
    if ext_override:
        extention = ext_override
    new_filename = os.path.join(folder, "{0}_lego{1}".format(base, extention))
    return new_filename


def get_new_size(base_image, brick_image, size=None):
    '''Returns a new size the first image should be so that the second one fits neatly in the longest axis'''
    new_size = base_image.size
    if size:
        scale_x, scale_y = size, size
    else:
        scale_x, scale_y = brick_image.size

    if new_size[0] > scale_x or new_size[1] > scale_y:
        if new_size[0] < new_size[1]:
            scale = new_size[1] / scale_y
        else:
            scale = new_size[0] / scale_x

        new_size = (int(round(new_size[0] / scale)) or 1,
                    int(round(new_size[1] / scale)) or 1)

    return new_size

def get_lego_palette(palette_mode):
    '''Gets the palette for the specified lego palette mode'''
    legos = palettes.legos()
    palette = legos[palette_mode]
    return palettes.extend_palette(palette)


def apply_thumbnail_effects(image, palette, dither):
    '''Apply effects on the reduced image before Legofying'''
    palette_image = Image.new("P", (1, 1))
    palette_image.putpalette(palette)
    return image.im.convert("P",
                        Image.FLOYDSTEINBERG if dither else Image.NONE,
                        palette_image.im)

def legofy_gif(base_image, brick_image, output_path, size, palette_mode, dither):
    '''Alternative function that legofies animated gifs, makes use of images2gif - uses numpy!'''
    im = base_image

    # Read original image duration
    original_duration = im.info['duration']

    # Split image into single frames
    frames = [frame.copy() for frame in ImageSequence.Iterator(im)]

    # Create container for converted images
    frames_converted = []

    print("Number of frames to convert: " + str(len(frames)))

    # Iterate through single frames
    for i, frame in enumerate(frames, 1):
        print("Converting frame number " + str(i))

        new_size = get_new_size(frame, brick_image, size)
        frame.thumbnail(new_size, Image.ANTIALIAS)
        if palette_mode:
            palette = get_lego_palette(palette_mode)
            frame = apply_thumbnail_effects(frame, palette, dither)
        new_frame = make_lego_image(frame, brick_image)
        frames_converted.append(new_frame)

    # Make use of images to gif function
    images2gif.writeGif(output_path, frames_converted, duration=original_duration/1000.0, dither=0, subRectangles=False)

def legofy_image(base_image, brick_image, output_path, size, palette_mode, dither):
    '''Legofy an image'''
    new_size = get_new_size(base_image, brick_image, size)
    base_image.thumbnail(new_size, Image.ANTIALIAS)
    if palette_mode:
        palette = get_lego_palette(palette_mode)
        base_image = apply_thumbnail_effects(base_image, palette, dither)
    make_lego_image(base_image, brick_image).save(output_path)

    print str(len(color_map)) + " colors"
    for color in color_map:
        print ("{0}, amount:{1}".format(color 
            if color not in reverse_palette_solid else reverse_palette_solid[color], color_map[color]))


def main(image_path, output_path=None, size=None,
         palette_mode=None, dither=False):
    '''Legofy image or gif with brick_path mask'''
    image_path = os.path.realpath(image_path)
    if not os.path.isfile(image_path):
        print('Image file "{0}" was not found.'.format(image_path))
        sys.exit(1)

    brick_path = os.path.join(os.path.dirname(__file__), "assets",
                              "bricks", "1x1.png")

    if not os.path.isfile(brick_path):
        print('Brick asset "{0}" was not found.'.format(brick_path))
        sys.exit(1)

    base_image = Image.open(image_path)
    brick_image = Image.open(brick_path)

    if palette_mode:
        print ("LEGO Palette {0} selected...".format(palette_mode.title()))
    elif dither:
        palette_mode = 'all'

    if image_path.lower().endswith(".gif") and base_image.is_animated:
        if output_path is None:
            output_path = get_new_filename(image_path)
        print("Animated gif detected, will now legofy to {0}".format(output_path))
        legofy_gif(base_image, brick_image, output_path, size, palette_mode, dither)
    else:
        if output_path is None:
            output_path = get_new_filename(image_path, '.png')
        print("Static image detected, will now legofy to {0}".format(output_path))
        legofy_image(base_image, brick_image, output_path, size, palette_mode, dither)

    base_image.close()
    brick_image.close()
    print("Finished!")
