import skia
from .functions import get_font, linespace, dpx
from .drawtext import DrawText


class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        self.zoom = 1

    def layout(self):
        self.zoom = self.parent.zoom
        weight = self.node.style['font-weight']
        style = self.node.style['font-style']

        px_size = float(self.node.style['font-size'][:-2])
        size = dpx(px_size * 0.75, self.zoom)
        self.font = get_font(size, weight, style)

        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)

    def paint(self):
        cmds = []
        color = self.node.style['color']
        cmds.append(
                DrawText(self.x, self.y, self.word, self.font, color))
        return cmds

    def should_paint(self):
        return True

    def paint_effects(self, cmds):
        return cmds

    def self_rect(self):
        return skia.Rect.MakeLTRB(self.x, self.y,
                                  self.x + self.width, self.y + self.height)
