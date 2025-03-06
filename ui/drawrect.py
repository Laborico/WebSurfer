from .functions2 import parse_color
import skia


# RR is for round corners
class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color))

        canvas.drawRRect(self.rrect, paint)


class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, canvas):
        paint = skia.Paint(
                Color=parse_color(self.color))

        canvas.drawRect(self.rect, paint)
