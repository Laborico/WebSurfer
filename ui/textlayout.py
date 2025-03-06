from .functions import get_font, linespace
from .drawtext import DrawText


class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

    def layout(self):
        weight = self.node.style['font-weight']
        style = self.node.style['font-style']

        size = float(self.node.style['font-size'][:-2]) * .75
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
