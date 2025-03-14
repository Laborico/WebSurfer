from .tag_selector import TagSelector
from .descendant_selector import DescendantSelector
from .pseudoclass_selector import PseudoclassSelector


INHERITED_PROPERTIES = {
        'font-size': '16px',
        'font-style': 'normal',
        'font-weight': 'normal',
        'color': 'black'
        }


class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        in_quote = False
        while self.i < len(self.s):
            cur = self.s[self.i]
            if cur == "'":
                in_quote = not in_quote
            if cur.isalnum() or cur in ',/#-.%()"\'' \
                    or (in_quote and cur == ':'):
                self.i += 1
            else:
                break

        if not (self.i > start):
            raise Exception('Parsing error')

        return self.s[start:self.i]

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception('Parsing error')

        self.i += 1

    def pair(self, until):
        prop = self.word()
        self.whitespace()
        self.literal(':')
        self.whitespace()
        val = self.until_chars(until)
        return prop.casefold(), val.strip()

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != '}':
            try:
                prop, val = self.pair([';', '}'])
                pairs[prop.casefold()] = val
                self.whitespace()
                self.literal(';')
                self.whitespace()
            except Exception:
                why = self.ignore_until([';', '}'])
                if why == ';':
                    self.literal(';')
                    self.whitespace()
                else:
                    break

        return pairs

    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None

    def selector(self):
        out = self.simple_selector()
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != '{':
            descendant = self.simple_selector()
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def parse(self):
        rules = []
        media = None
        self.whitespace()
        while self.i < len(self.s):
            try:
                if self.s[self.i] == '@' and not media:
                    prop, val = self.media_query()
                    if prop == 'prefers-color-scheme' and \
                            val in ['dark', 'light']:
                        media = val
                    self.whitespace()
                    self.literal('{')
                    self.whitespace()
                elif self.s[self.i] == '}' and media:
                    self.literal('}')
                    media = None
                    self.whitespace()
                else:
                    selector = self.selector()
                    self.literal('{')
                    self.whitespace()
                    body = self.body()
                    self.literal('}')
                    self.whitespace()
                    rules.append((media, selector, body))
            except Exception:
                why = self.ignore_until(['}'])
                if why == '}':
                    self.literal('}')
                    self.whitespace()
                else:
                    break
        return rules

    def until_chars(self, chars):
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in chars:
            self.i += 1
        return self.s[start:self.i]

    def media_query(self):
        self.literal('@')
        assert self.word() == 'media'

        self.whitespace()
        self.literal('(')
        self.whitespace()
        prop, val = self.pair([')'])
        self.whitespace()
        self.literal(')')
        return prop, val

    def simple_selector(self):
        out = TagSelector(self.word().casefold())
        if self.i < len(self.s) and self.s[self.i] == ':':
            self.literal(':')
            pseudoclass = self.word().casefold()
            out = PseudoclassSelector(pseudoclass, out)
        return out


DEFAULT_STYLE_SHEET = CSSParser(open('browser.css').read()).parse()
