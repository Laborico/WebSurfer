class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}
        self.animations = {}
        self.is_focused = False
        self.layout_object = None

    def __repr__(self):
        return repr(self.text)
