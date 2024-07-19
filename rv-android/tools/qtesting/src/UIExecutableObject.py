class UIExecutableObject:

    def __init__(self, cis, pkg_name, class_name):
        self.cis = cis
        self.pkg_name = pkg_name
        self.class_name = class_name
        self.isListView = False
        self.clickable = ''
        self.long_clickable = ''
        self.scrollable = ''
        self.checkable = ''
        self.text = ''
        self.resource_id = ''
        self.content_desc = ''
        self.index = ''
        self.instance = ''
        self.id_instance = ''
        self.clickable = False
        self.long_clickable = False
        self.scrollable = False
        self.checkable = False
        self.enabled = False

    def set_event_property(self, clickable, long_clickable, scrollable, checkable, text, resource_id, content_desc, index, enabled, instance, id_instance):
        self.clickable = clickable
        self.long_clickable = long_clickable
        self.scrollable = scrollable
        self.checkable = checkable
        self.text = text
        self.resource_id = resource_id
        self.content_desc = content_desc
        self.index = index
        self.enabled = enabled
        self.instance = instance
        self.id_instance = id_instance

    def set_clickable(self, clickable):
        self.clickable = clickable

    def set_long_clickable(self, long_clickable):
        self.long_clickable = long_clickable

    def set_scrollable(self, scrollable):
        self.scrollable = scrollable

    def set_checkable(self, checkable):
        self.checkable = checkable

    def get_class_name(self):
        return self.class_name

    def has_multi_lines_text(self):
        if '\n' in self.text:
            return True
        else:
            return False

    def get_first_line_text(self):
        return self.text.split('\n')[0]
