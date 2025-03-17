from .blocklayout import BlockLayout
from .variables import HSTEP, VSTEP
from .functions import dpx
from .transform import Transform
import skia


class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        self.parent = None
        self.previous = None
        self.children = []
        self.layout_object = self

    def layout(self, width, zoom):
        self.zoom = zoom
        child = BlockLayout(self.node, self, None, self.frame)
        self.children.append(child)

        self.width = width - 2 * dpx(HSTEP, self.zoom)
        self.x = dpx(HSTEP, self.zoom)
        self.y = dpx(VSTEP, self.zoom)
        child.layout()
        self.height = child.height

    def paint(self):
        return []

    def should_paint(self):
        return True

    def paint_effects(self, cmds):
        if self.frame != self.frame.tab.root_frame and self.frame.scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x, self.y,
                self.x + self.width, self.y + self.height)
            cmds = [Transform((0, - self.frame.scroll), rect, self.node, cmds)]

        return cmds
