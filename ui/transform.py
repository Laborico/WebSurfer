from .visualeffect import VisualEffect
from .functions2 import map_translation


class Transform(VisualEffect):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children, node)
        self.self_rect = rect
        self.translation = translation

    def execute(self, canvas):
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)

        for cmd in self.children:
            cmd.execute(canvas)
        if self.translation:
            canvas.restore()

    def clone(self, child):
        return Transform(self.translation, self.self_rect, self.node, [child])

    def map(self, rect):
        return map_translation(rect, self.translation)

    def unmap(self, rect):
        return map_translation(rect, self.translation, True)

    def __repr__(self):
        if self.translation:
            (x, y) = self.translation
            return 'Transform(translate({}, {}))'.format(x, y)
        else:
            return 'Transform(<no-op>)'
