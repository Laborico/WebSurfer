import ctypes
import sdl2
import skia
import sys
from .variables import FONTS
from .blend import Blend
from .drawrect import DrawRRect
from .transform import Transform
from .functions2 import parse_transform


# Memoazation for the win, text caching to improve text rendering speed
def get_font(size, weight, style):
    key = (weight, style)
    if key not in FONTS:
        if weight == 'bold':
            skia_weight = skia.FontStyle.kBold_Weight
        else:
            skia_weight = skia.FontStyle.kNormal_Weight

        if style == 'italic':
            skia_style = skia.FontStyle.kItalic_Slant
        else:
            skia_style = skia.FontStyle.kUpright_Slant

        skia_width = skia.FontStyle.kNormal_Width
        style_info = skia.FontStyle(skia_weight, skia_width, skia_style)

        font = skia.Typeface('Arial', style_info)
        FONTS[key] = font

    return skia.Font(FONTS[key], size)


def paint_tree(layout_object, display_list):
    cmds = []
    if layout_object.should_paint():
        cmds = layout_object.paint()

    for child in layout_object.children:
        paint_tree(child, cmds)

    if layout_object.should_paint():
        cmds = layout_object.paint_effects(cmds)

    display_list.extend(cmds)


def mainloop(browser):
    event = sdl2.SDL_Event()
    while True:
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
                break
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))

        browser.composite_raster_and_draw()
        browser.schedule_animation_frame()


def linespace(font):
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent


def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style.get('opacity', '1.0'))

    blend_mode = node.style.get('mix-blend-mode')

    translation = parse_transform(
            node.style.get('transform', ''))

    if node.style.get('overflow', 'visible') == 'clip':
        border_radius = float(node.style.get(
            'border-radius', '0px')[:-2])

        if not blend_mode:
            blend_mode = 'source-over'

        cmds.append(Blend(1.0, 'destination-in', None, [
            DrawRRect(rect, border_radius, 'white')
            ]))

    blend_op = Blend(opacity, blend_mode, node, cmds)
    node.blend_op = blend_op

    return [Transform(translation, rect, node, [blend_op])]


def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


def add_parent_pointers(nodes, parent=None):
    for node in nodes:
        node.parent = parent
        add_parent_pointers(node.children, node)


def absolute_to_local(display_item, rect):
    parent_chain = []
    while display_item.parent:
        parent_chain.append(display_item.parent)
        display_item = display_item.parent
    for parent in reversed(parent_chain):
        rect = parent.unmap(rect)
    return rect


def local_to_absolute(display_item, rect):
    while display_item.parent:
        rect = display_item.parent.map(rect)
        display_item = display_item.parent
    return rect
