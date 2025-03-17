from .drawrect import DrawRRect
from .drawtext import DrawText
from .drawline import DrawLine
from .embedlayout import EmbedLayout
from html_parser.text import Text
from .functions import paint_visual_effects, dpx, paint_outline, linespace
from .variables import INPUT_WIDTH_PX
import skia


class InputLayout(EmbedLayout):
    def __init__(self, node, parent, previous, frame):
        super().__init__(node, parent, previous, frame)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get('background-color', 'transparent')

        if bgcolor != 'transparent':
            radius = dpx(float(
                    self.node.style.get(
                        'border-radius', '0px')[:-2]), self.zoom)
            cmds.append(DrawRRect(
                self.self_rect(), radius, bgcolor))

        if self.node.tag == 'input':
            text = self.node.attributes.get('value', '')
        elif self.node.tag == 'button':
            if len(self.node.children) == 1 and \
                    isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print('Ignoring HTML contents inside button')
                text = ''

        color = self.node.style['color']
        cmds.append(
                DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused and self.node.tag == 'input':
            cx = self.x + self.font.measureText(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, color, 1))

        return cmds

    def layout(self):
        super().layout()

        self.width = dpx(INPUT_WIDTH_PX, self.zoom)
        self.height = linespace(self.font)

        self.ascent = -self.height
        self.descent = 0

    def should_paint(self):
        return True

    def self_rect(self):
        return skia.Rect.MakeLTRB(self.x, self.y,
                                  self.x + self.width, self.y + self.height)

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), self.zoom)
        return cmds
