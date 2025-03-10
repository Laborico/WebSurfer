import skia
from .variables import NAMED_COLORS


def parse_blend_mode(blend_mode_str):
    if blend_mode_str == 'multiply':
        return skia.BlendMode.kMultiply
    elif blend_mode_str == 'difference':
        return skia.BlendMode.kDifference
    elif blend_mode_str == 'destination-in':
        return skia.BlendMode.kDstIn
    elif blend_mode_str == 'source-over':
        return skia.BlendMode.kSrcOver
    else:
        return skia.BlendMode.kSrcOver


def parse_color(color):
    if color.startswith('#') and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return skia.Color(r, g, b)
    elif color.startswith('#') and len(color) == 9:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = int(color[7:9], 16)
        return skia.Color(r, g, b, a)
    elif color in NAMED_COLORS:
        return parse_color(NAMED_COLORS[color])
    else:
        return skia.ColorBLACK
