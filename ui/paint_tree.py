from .iframelayout import IframeLayout


def paint_tree(layout_object, display_list):
    cmds = layout_object.paint()

    if isinstance(layout_object, IframeLayout) and \
            layout_object.node.frame and layout_object.node.frame.loaded:
        paint_tree(layout_object.node.frame.document, cmds)
    else:
        for child in layout_object.children:
            paint_tree(child, cmds)

    cmds = layout_object.paint_effects(cmds)
    display_list.extend(cmds)
