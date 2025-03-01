from .rectangle import Rect


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.rect = Rect(x1, y1, x1 + font.measure(text),
                         y1 + font.metrics('linespace'))
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_text(
                self.rect.left, self.rect.top - scroll,
                text=self.text,
                font=self.font,
                anchor='nw',
                fill=self.color
                )
