from html_parser.parser import HTMLParser
from html_parser.element import Element
from html_parser.text import Text
from css_parser.parser import CSSParser
from css_parser.functions import cascade_priority, style
from processing.task import Task
from .functions import tree_to_list
from .variables import BROKEN_IMAGE, SCROLL_STEP, VSTEP
from .documentlayout import DocumentLayout
from .functions import is_focusable, get_tabindex, dpx
from .functions2 import absolute_bounds_for_objs
from css_parser.parser import DEFAULT_STYLE_SHEET, INHERITED_PROPERTIES
import skia
import urllib
import math


class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.tab = tab
        self.parent_frame = parent_frame
        self.frame_element = frame_element
        self.needs_style = False
        self.needs_layout = False

        self.document = None
        self.scroll = 0
        self.scroll_changed_in_frame = True
        self.needs_focus_scroll = False
        self.nodes = None
        self.url = None
        self.js = None
        self.loaded = False

        self.frame_width = 0
        self.frame_height = 0

        self.window_id = len(self.tab.window_id_to_frame)
        self.tab.window_id_to_frame[self.window_id] = self

    def set_needs_render(self):
        self.needs_style = True
        self.tab.set_needs_paint()

    def set_needs_layout(self):
        self.needs_layout = True
        self.tab.set_needs_paint()

    def allowed_request(self, url):
        return self.allowed_origins is None or \
            url.origin() in self.allowed_origins

    def load(self, url, payload=None):
        self.loaded = False
        self.zoom = 1
        self.scroll = 0
        self.url = url
        self.scroll_changed_in_frame = True
        headers, body = url.request(self.url, payload)
        body = body.decode('utf8', 'replace')

        self.allowed_origins = None
        if 'content-security-policy' in headers:
            csp = headers['content-security-policy'].split()
            if len(csp) > 0 and csp[0] == 'default-src':
                self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        if self.js:
            self.js.discarded = True
        self.js = self.tab.get_js(url)
        self.js.add_window(self)

        scripts = [node.attributes['src'] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == 'script'
                   and 'src' in node.attributes]

        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print('Blocked script', script, 'due to CSP')
                continue
            try:
                header, body = script_url.request(url)
            except Exception:
                continue
            body = body.decode('utf8', 'replace')
            task = Task(self.js.run, script_url, body, self.window_id)
            self.tab.task_runner.schedule_task(task)

        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes['href']
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == 'link'
                 and node.attributes.get('rel') == 'stylesheet'
                 and 'href' in node.attributes]

        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print('Blocked style', link, 'due to CSP')
                continue
            try:
                header, body = style_url.request(url)
            except Exception:
                continue
            self.rules.extend(CSSParser(
                body.decode('utf8', 'replace')).parse())

        images = [node for node in tree_to_list(self.nodes, [])
                  if isinstance(node, Element)
                  and node.tag == 'img']

        for img in images:
            try:
                src = img.attributes.get('src', '')
                image_url = url.resolve(src)

                assert self.allowed_request(image_url), \
                    'Blocked load of ' + str(image_url) + ' due to CSP'

                header, body = image_url.request(url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)

                assert img.image, \
                    'Failed to recognize image format for ' + str(image_url)
            except Exception as e:
                print('Image', img.attributes.get('src', ''), 'crashed', e)
                img.image = BROKEN_IMAGE

        iframes = [node for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == 'iframe'
                   and 'src' in node.attributes]

        for iframe in iframes:
            document_url = url.resolve(iframe.attributes['src'])
            if not self.allowed_request(document_url):
                print('Blocked iframe', document_url, 'due to CSP')
                iframe.frame = None
                continue
            iframe.frame = Frame(self.tab, self, iframe)
            task = Task(iframe.frame.load, document_url)
            self.tab.task_runner.schedule_task(task)

        self.set_needs_render()
        self.loaded = True

    def render(self):
        if self.needs_style:
            if self.tab.dark_mode:
                INHERITED_PROPERTIES['color'] = 'white'
            else:
                INHERITED_PROPERTIES['color'] = 'black'
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes, self)
            self.document.layout(self.frame_width, self.tab.zoom)
            self.needs_paint = True
            self.needs_layout = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll

    def advance_tab(self):
        focusable_nodes = [node for node in tree_to_list(self.nodes, [])
                           if isinstance(node, Element) and is_focusable(node)
                           and get_tabindex(node) >= 0]
        focusable_nodes.sort(key=get_tabindex)

        if self.tab.focus in focusable_nodes:
            idx = focusable_nodes.index(self.tab.focus) + 1
        else:
            idx = 0

        if idx < len(focusable_nodes):
            self.focus_element(focusable_nodes[idx])
            self.tab.browser.focus_content()
        else:
            self.focus_element(None)
            self.tab.browser.focus_addressbar()
        self.set_needs_render()

    def focus_element(self, node):
        if node and node != self.tab.focus:
            self.needs_focus_scroll = True

        if self.tab.focus:
            self.tab.focus.is_focused = False

        if self.tab.focused_frame and self.tab.focused_frame != self:
            self.tab.focused_frame.set_needs_render()
        self.tab.focus = node
        self.tab.focused_frame = self

        if node:
            node.is_focused = True

        self.set_needs_render()

    def activate_element(self, elt):
        if elt.tag == 'input':
            elt.attributes['value'] = ''
            self.set_needs_render()
        elif elt.tag == 'a' and 'href' in elt.attributes:
            url = self.url.resolve(elt.attributes['href'])
            self.load(url)
        elif elt.tag == 'button':
            while elt:
                if elt.tag == 'form' and 'action' in elt.attributes:
                    self.submit_form(elt)
                    return
                elt = elt.parent

    def submit_form(self, elt):
        if self.js.dispatch_event('submit', elt, self.window_id):
            return
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == 'input'
                  and 'name' in node.attributes]

        body = ''
        for input in inputs:
            name = input.attributes['name']
            value = input.attributes.get('value', '')
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += '&' + name + '=' + value
        body = body[1:]

        url = self.url.resolve(elt.attributes['action'])
        self.load(url, body)

    def keypress(self, char):
        if self.tab.focus and self.tab.focus.tag == 'input':
            if 'value' not in self.tab.focus.attributes:
                self.activate_element(self.tab.focus)
            if self.js.dispatch_event(
                    'keydown', self.tab.focus, self.window_id):
                return
            self.tab.focus.attributes['value'] += char
            self.set_needs_render()

    def scrolldown(self):
        self.scroll = self.clamp_scroll(self.scroll + SCROLL_STEP)
        self.scroll_changed_in_frame = True

    def scroll_to(self, elt):
        assert not (self.needs_style or self.needs_layout)
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.node == self.tab.focus
        ]
        if not objs:
            return
        obj = objs[0]

        if self.scroll < obj.y < self.scroll + self.frame_height:
            return
        new_scroll = obj.y - SCROLL_STEP

        self.scroll = self.clamp_scroll(new_scroll)
        self.scroll_changed_in_frame = True
        self.tab.set_needs_paint()

    def click(self, x, y):
        self.focus_element(None)
        y += self.scroll
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_objs(obj).intersects(
                    loc_rect)]
        if not objs:
            return

        elt = objs[-1].node
        if elt and self.js.dispatch_event('click', elt, self.window_id):
            return

        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == 'iframe':
                abs_bounds = absolute_bounds_for_objs(elt.layout_object)

                border = dpx(1, elt.layout_object.zoom)
                new_x = x - abs_bounds.left() - border
                new_y = y - abs_bounds.top() - border
                elt.frame.click(new_x, new_y)
                return
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
            elt = elt.parent

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height + 2*VSTEP)
        maxscroll = height - self.frame_height
        return max(0, min(scroll, maxscroll))
