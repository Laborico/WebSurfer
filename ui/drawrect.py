class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
                self.rect.left, self.rect.top - scroll,
                self.rect.right, self.rect.bottom - scroll,
                width=0,
                fill=self.color
                )
