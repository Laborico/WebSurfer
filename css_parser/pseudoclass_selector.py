class PseudoclassSelector:
    def __init__(self, pseudoclass, base):
        self.pseudoclass = pseudoclass
        self.base = base
        self.priority = self.base.priority

    def matches(self, node):
        if not self.base.matches(node):
            return False
        if self.pseudoclass == 'focus':
            return node.is_focused
        else:
            return False
