from .parser import INHERITED_PROPERTIES
from .parser import CSSParser
from html_parser.element import Element
from ui.variables import REFRESH_RATE_SEC
from ui.numericanimation import NumericAnimation


def style(node, rules, tab):
    old_style = node.style
    node.style = {}

    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    for media, selector, body in rules:
        if media:
            if (media == 'dark') != tab.dark_mode:
                continue
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

    if old_style:
        transitions = diff_styles(old_style, node.style)
        for property, (old_value, new_value, num_frames) \
                in transitions.items():
            if property == 'opacity':
                tab.set_needs_render()
                animation = NumericAnimation(old_value, new_value, num_frames)
                node.animations[property] = animation
                node.style[property] = animation.animate()

    for child in node.children:
        style(child, rules, tab)


def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


def cascade_priority(rule):
    media, selector, body = rule
    return selector.priority


def parse_transition(value):
    properties = {}
    if not value:
        return properties
    for item in value.split(','):
        property, duration = item.split(' ', 1)
        frames = int(float(duration[:-1]) / REFRESH_RATE_SEC)
        properties[property] = frames
    return properties


def diff_styles(old_style, new_style):
    transitions = {}
    for property, num_frames in \
            parse_transition(new_style.get('transition')).items():
        if property not in old_style:
            continue
        if property not in new_style:
            continue
        old_value = old_style[property]
        new_value = new_style[property]
        if old_value == new_value:
            continue
        transitions[property] = (old_value, new_value, num_frames)
    return transitions


def parse_outline(outline_str):
    if not outline_str:
        return None
    values = outline_str.split(' ')
    if len(values) != 3:
        return None
    if values[1] != 'solid':
        return None
    return int(values[0][:-2]), values[2]
