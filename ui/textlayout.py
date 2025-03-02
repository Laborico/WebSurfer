from .functions import get_font
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

        if style == 'normal':
            style = 'roman'

        size = int(float(self.node.style['font-size'][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(' ')
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics('linespace')

    def paint(self):
        color = self.node.style['color']
        return [DrawText(self.x, self.y, self.word, self.font, color)]

    def should_paint(self):
        return True
