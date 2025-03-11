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


def map_translation(rect, translation, reversed=False):
    if not translation:
        return rect
    else:
        (x, y) = translation
        matrix = skia.Matrix()
        if reversed:
            matrix.setTranslate(-x, -y)
        else:
            matrix.setTranslate(x, y)
        return matrix.mapRect(rect)


def absolute_bounds_for_objs(obj):
    rect = skia.Rect.MakeXYWH(obj.x, obj.y, obj.width, obj.height)
    cur = obj.node
    while cur:
        rect = map_translation(rect, parse_transform(
                cur.style.get('transform', '')))
        cur = cur.parent
    return rect


def parse_transform(transform_str):
    if transform_str.find('translate(') < 0:
        return None

    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')
    (x_px, y_px) = transform_str[left_paren + 1: right_paren].split(',')
    return (float(x_px[:-2]), float(y_px[:-2]))
