import skia
from .functions2 import parse_blend_mode


class Blend:
    def __init__(self, opacity, blend_mode, children):
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.should_save = self.blend_mode or self.opacity < 1

        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

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
