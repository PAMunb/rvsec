import os

class App(object):
    """
    this class describes an app
    """

    def __init__(self, app_path):
        """
        create an App instance
        :param app_path: local file path of app
        :return:
        """
        assert app_path is not None

        self.path = os.path.join(app_path)
        self.name = os.path.basename(app_path)

        # from androguard.core.bytecodes.apk import APK
        # self.apk = APK(self.path)
        # self.package_name = self.apk.get_package()
        # self.main_activity = self.apk.get_main_activity()
        # self.permissions = self.apk.get_permissions()
        # self.activities = self.apk.get_activities()
        # self.possible_broadcasts = self.get_possible_broadcasts()
