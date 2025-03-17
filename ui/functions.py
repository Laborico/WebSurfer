import ctypes
import sdl2
import skia
import sys
from .variables import FONTS
from .blend import Blend
from .drawrect import DrawRRect
from .transform import Transform
from .drawoutline import DrawOutline
from .functions2 import parse_transform
from css_parser.functions import parse_outline
from connection.url import URL


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


def mainloop(browser):
    event = sdl2.SDL_Event()
    ctrl_down = False
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
                if ctrl_down:
                    if event.key.keysym.sym == sdl2.SDLK_EQUALS:
                        browser.increment_zoom(True)
                    elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                        browser.increment_zoom(False)
                    elif event.key.keysym.sym == sdl2.SDLK_0:
                        browser.reset_zoom()
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
                    elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                        browser.go_back()
                    elif event.key.keysym.sym == sdl2.SDLK_l:
                        browser.focus_addressbar()
                    elif event.key.keysym.sym == sdl2.SDLK_t:
                        browser.new_tab_internal(
                                URL('https://www.wikipedia.org'))
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        browser.handle_quit()
                        sdl2.SDL_Quit()
                        sys.exit()
                        break

                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    browser.handle_tab()
                elif event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                        event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = True
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()

            elif event.type == sdl2.SDL_KEYUP:
                if event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                        event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = False
            elif event.type == sdl2.SDL_TEXTINPUT and not ctrl_down:
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


def dpx(css_px, zoom):
    return css_px * zoom


def is_focusable(node):
    if get_tabindex(node) < 0:
        return False
    elif 'tabindex' in node.attributes:
        return True
    else:
        return node.tag in ['input', 'button', 'a']


def get_tabindex(node):
    tabindex = int(node.attributes.get('tabindex', '9999999'))
    return 9999999 if tabindex == 0 else tabindex


def paint_outline(node, cmds, rect, zoom):
    outline = parse_outline(node.style.get('outline'))
    if not outline:
        return
    thickness, color = outline
    cmds.append(DrawOutline(rect, color, dpx(thickness, zoom)))


def parse_image_rendering(quality):
    if quality == 'high-quality':
        return skia.FilterQuality.kHigh_FilterQuality
    elif quality == 'crisp-edges':
        return skia.FilterQuality.kLow_FilterQuality
    else:
        return skia.FilterQuality.kMedium_FilterQuality


def font(style, zoom):
    weight = style["font-weight"]
    variant = style["font-style"]
    size = None

    try:
        size = float(style["font-size"][:-2]) * 0.75
    except Exception:
        size = 16
    font_size = dpx(size, zoom)

    return get_font(font_size, weight, variant)
