from .parser import INHERITED_PROPERTIES
from .parser import CSSParser
from html_parser.element import Element


def style(node, rules):
    node.style = {}

    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    for selector, body in rules:
        if not selector.matches(node):
            continue
        for property, value in body.items():
            node.style[property] = value

    if isinstance(node, Element) and 'style' in node.attributes:
        pairs = CSSParser(node.attributes['style']).body()
        for property, value in pairs.items():
            node.style[property] = value

    # Manges % in font sizes
    if node.style['font-size'].endswith('%'):
        if node.parent:
            parent_font_size = node.parent.style['font-size']
        else:
            parent_font_size = INHERITED_PROPERTIES['font-size']
        node_pct = float(node.style['font-size'][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style['font-size'] = str(node_pct * parent_px) + 'px'

    for child in node.children:
        style(child, rules)


def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


def cascade_priority(rule):
    selector, body = rule
    return selector.priority
