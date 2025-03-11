from .paintcommand import PaintCommand


class DrawCompositedLayer(PaintCommand):
    def __init__(self, composited_layer):
        self.composited_layer = composited_layer
        super().__init__(
                self.composited_layer.composited_bounds())

    def __repr__(self):
        return 'DrawCompositedLayer()'

    def execute(self, canvas):
        layer = self.composited_layer
        if not layer.surface:
            return
        bounds = layer.composited_bounds()
        layer.surface.draw(canvas, bounds.left(), bounds.top())
