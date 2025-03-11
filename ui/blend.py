import skia
from .functions2 import parse_blend_mode
from .visualeffect import VisualEffect


class Blend(VisualEffect):
    def __init__(self, opacity, blend_mode, node, children):
        super().__init__(skia.Rect.MakeEmpty(), children, node)
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.should_save = self.blend_mode or self.opacity < 1

        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

        if self.should_save:
            self.needs_compositing = True

    def execute(self, canvas):
        paint = skia.Paint(
                Alphaf=self.opacity,
                BlendMode=parse_blend_mode(self.blend_mode))

        if self.should_save:
            canvas.saveLayer(None, paint)

        for cmd in self.children:
            cmd.execute(canvas)

        if self.should_save:
            canvas.restore()

    def __repr__(self):
        args = ''
        if self.opacity < 1:
            args += ', opacity={}'.format(self.opacity)
        if self.blend_mode:
            args += ', blend_mode={}'.format(self.blend_mode)
        if not args:
            args = ', <no-op>'
        return 'Blend({})'.format(args[2:])

    def clone(self, child):
        return Blend(self.opacity, self.blend_mode, self.node, [child])

    def map(self, rect):
        if self.children and isinstance(self.children[-1], Blend) and \
                self.children[-1].blend_mode == 'destination-in':
            bounds = rect.makeOffset(0.0, 0.0)
            bounds.intersect(self.children[-1].rect)
            return bounds
        else:
            return rect

    def unmap(self, rect):
        return rect
