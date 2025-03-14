from .blocklayout import BlockLayout
from .variables import WIDTH, HSTEP, VSTEP
from .functions import dpx


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []
        self.layout_object = self

    def layout(self, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
        child.layout()
        self.height = child.height

    def paint(self):
        return []

    def should_paint(self):
        return True

    def paint_effects(self, cmds):
        return cmds
