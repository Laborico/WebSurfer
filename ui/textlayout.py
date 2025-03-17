import skia
from .functions import linespace, font
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
        self.font = font(self.node.style, self.zoom)

        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = linespace(self.font)
        self.ascent = self.font.getMetrics().fAscent * 1.25
        self.descent = self.font.getMetrics().fDescent * 1.25

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
