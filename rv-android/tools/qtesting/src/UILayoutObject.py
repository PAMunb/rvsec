class UILayoutObject:

    def __init__(self, cis, pkg_name, class_name):
        self.cis = cis
        self.pkg_name = pkg_name
        self.class_name = class_name
        self.isListView = False

    def setIsListView(self, isListView):
        self.isListView = isListView
