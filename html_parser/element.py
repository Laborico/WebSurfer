class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.is_focused = False
        self.style = {}
        self.animations = {}

    def __repr__(self):
        return '<' + self.tag + '>'
