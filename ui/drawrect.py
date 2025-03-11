from .functions2 import parse_color
from .paintcommand import PaintCommand
import skia


# RR is for round corners
class DrawRRect(PaintCommand):
    def __init__(self, rect, radius, color):
        super().__init__(rect)
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color))

        canvas.drawRRect(self.rrect, paint)


class DrawRect(PaintCommand):
    def __init__(self, rect, color):
        super().__init__(rect)
        self.rect = rect
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color))

        canvas.drawRect(self.rect, paint)

    def __repr__(self):
        return ('DrawRect(top={} left={} bottom={} right={} color{})').format(
                self.top, self.left, self.bottom, self.right, self.color)
