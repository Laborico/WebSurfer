import skia
from .textlayout import TextLayout
from .functions import paint_outline, parse_outline


class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.zoom = self.parent.zoom
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = 0
            return

        max_ascent = max([-child.ascent for child in self.children])
        baseline = self.y + max_ascent

        for child in self.children:
            if isinstance(child, TextLayout):
                child.y = baseline + child.ascent / 1.25
            else:
                child.y = baseline + child.ascent
        max_descent = max([child.descent
                           for child in self.children])
        self.height = max_ascent + max_descent

    def paint(self):
        return []

    def should_paint(self):
        return True

    def paint_effects(self, cmds):
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            outline_str = child.node.parent.style.get('outline')
            if parse_outline(outline_str):
                outline_rect.join(child.self_rect())
                outline_node = child.node.parent
        if outline_node:
            paint_outline(outline_node, cmds, outline_rect, self.zoom)
        return cmds
