class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height,
                 display_list, composited_updates, focus):
        self.url = url
        self.scroll = scroll
        self.root_frame_focused = root_frame_focused
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates
        self.focus = focus
