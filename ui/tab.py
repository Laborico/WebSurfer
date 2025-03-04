from html_parser.parser import HTMLParser
from html_parser.element import Element
from html_parser.text import Text
from css_parser.parser import DEFAULT_STYLE_SHEET
from css_parser.functions import tree_to_list, cascade_priority, style
from css_parser.parser import CSSParser
from .documentlayout import DocumentLayout
from .functions import paint_tree
from .variables import VSTEP, SCROLL_STEP
from js_interpreter.jscontext import JSContext
import urllib.parse


class Tab:
    def __init__(self, tab_height):
        self.url = None
        self.tab_height = tab_height
        self.history = []
        self.focus = None

    def draw(self, canvas, offset):

        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - offset, canvas)

    def load(self, url, payload=None):
        self.history.append(url)
        self.url = url
        body = url.request(payload)
        self.scroll = 0

        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()

        scripts = [node.attributes['src'] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == 'script'
                   and 'src' in node.attributes]

        self.js = JSContext(self)

        for script in scripts:
            script_url = url.resolve(script)
            try:
                body = script_url.request()
            except Exception:
                continue
            self.js.run(script, body)

        links = [node.attributes['href']
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == 'link'
                 and node.attributes.get('rel') == 'stylesheet'
                 and 'href' in node.attributes]

        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except Exception:
                continue
            self.rules.extend(CSSParser(body).parse())
        style(self.nodes, sorted(self.rules, key=cascade_priority))

        self.display_list = []
        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        paint_tree(self.document, self.display_list)

        self.render()

    def scrolldown(self):
        max_y = max(self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def click(self, x, y):
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll

        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]

        if not objs:
            return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == 'a' and 'href' in elt.attributes:
                if self.js.dispatch_event('click', elt):
                    return
                url = self.url.resolve(elt.attributes['href'])
                return self.load(url)
            elif elt.tag == 'input':
                if self.js.dispatch_event('click', elt):
                    return
                elt.attributes['value'] = ''
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == 'button':
                if self.js.dispatch_event('click', elt):
                    return
                while elt:
                    if elt.tag == 'form' and 'action' in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent

            elt = elt.parent

        self.render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event('keydown', self.focus):
                return
            self.focus.attributes['value'] += char
            self.render()

    def submit_form(self, elt):
        if self.js.dispatch_event('submit', elt):
            return
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == 'input'
                  and 'name' in node.attributes]

        body = ''
        for input in inputs:
            name = input.attributes['name']
            value = input.attributes.get('value', '')
            body += '&' + name + '=' + value
        body = body[1:]

        name = urllib.parse.quote(name)
        value = urllib.parse.quote(value)

        url = self.url.resolve(elt.attributes['action'])
        self.load(url, body)
