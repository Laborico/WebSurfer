from .blocklayout import BlockLayout
from .variables import WIDTH, HSTEP, VSTEP


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []

    def should_paint(self):
        return True

    def paint_effects(self, cmds):
        return cmds
