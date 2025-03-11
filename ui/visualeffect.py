class VisualEffect:
    def __init__(self, rect, children, node=None):
        self.rect = rect.makeOffset(0.0, 0.0)
        self.children = children
        for child in self.children:
            self.rect.join(child.rect)
        self.node = node
        self.needs_compositing = any([
            child.needs_compositing for child in self.children
            if isinstance(child, VisualEffect)
            ])
