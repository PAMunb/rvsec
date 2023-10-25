import os

from androguard.core.bytecodes.apk import APK


class App(object):
    """
    this class describes an app
    """

#TODO criar e usar getters

    def __init__(self, app_path):
        """
        create an App instance
        :param app_path: local file path of app
        :return:
        """
        assert app_path is not None

        self.path = os.path.join(app_path)
        #TODO mudar para filename ... e pegar o app_name via androguard
        self.name = os.path.basename(app_path)

        self.apk = APK(self.path)
        self.package_name = self.apk.get_package()
        self.sdk_target = self.apk.get_effective_target_sdk_version()
        self.permissions = self.apk.get_permissions()
