from .variables import INPUT_WIDTH_PX
from .drawrect import DrawRRect
from .drawtext import DrawText
from .drawline import DrawLine
from .functions import get_font, linespace, paint_visual_effects
from html_parser.text import Text
import skia


class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.width = INPUT_WIDTH_PX

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get('background-color', 'transparent')

        if bgcolor != 'transparent':
            radius = float(
                    self.node.style.get(
                        'border-radius', '0px')[:-2])
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))

        if self.node.tag == 'input':
            text = self.node.attributes.get('value', '')
        elif self.node.tag == 'button':
            if len(self.node.children) == 1 and \
                    isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print('Ignoring HTML contens inside button')
                text = ''

        color = self.node.style['color']
        cmds.append(
                DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, 'black', 1))

        return cmds

    def layout(self):
        weight = self.node.style['font-weight']
        style = self.node.style['font-style']

        size = float(self.node.style['font-size'][:-2]) * .75
        self.font = get_font(size, weight, style)

        self.width = INPUT_WIDTH_PX

        if self.previous:
            space = self.previous.font.measureText(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def should_paint(self):
        return True

    def self_rect(self):
        return skia.Rect.MakeLTRB(self.x, self.y,
                                  self.x + self.width, self.y + self.height)

    def paint_effects(self, cmds):
        return paint_visual_effects(self.node, cmds, self.self_rect())
