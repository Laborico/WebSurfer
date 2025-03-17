class AttributeParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        if self.i < len(self.s) and self.s[self.i] == literal:
            self.i += 1
            return True
        return False

    def word(self, allow_quotes=False):
        start = self.i
        in_quote = False
        quoted = False

        while self.i < len(self.s):
            cur = self.s[self.i]
            if not cur.isspace() and cur not in '=\"\'':
                self.i += 1
            elif allow_quotes and cur in '\"\'':
                in_quote = not in_quote
                quoted = True
                self.i += 1
            elif in_quote and (cur.isspace() or cur == '='):
                self.i += 1
            else:
                break

        if self.i == start:
            self.i = len(self.s)
            return ''
        if quoted:
            return self.s[start+1:self.i-1]

        return self.s[start:self.i]

    def parse(self):
        attributes = {}
        tag = None

        tag = self.word().casefold()
        while self.i < len(self.s):
            self.whitespace()
            key = self.word()
            if self.literal('='):
                value = self.word(allow_quotes=True)
                attributes[key.casefold()] = value
            else:
                attributes[key.casefold()] = ''

        return (tag, attributes)
