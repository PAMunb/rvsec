import os

from androguard.core.bytecodes.apk import APK


class App(object):
    """
    The App class represents an Android application, extracting metadata such as
    package name, permissions, and SDK version using Androguard.

    ### Architectural Decisions:
    - Uses Androguard to statically analyze APKs without requiring execution.
    - Maintains an object-oriented representation of app attributes for easy access.
    - Supports retrieval of security-relevant properties for runtime monitoring.

    ### Role in the System:
    - Serves as the primary interface for working with Android apps in experiments.
    - Facilitates security and behavior analysis by providing structured metadata.
    - Enables automated decision-making regarding instrumentation and test execution.
    """

    def __init__(self, app_path):
        """
        create an App instance
        :param app_path: local file path of app
        :return:
        """
        assert app_path is not None

        self.path = os.path.join(app_path)
        # TODO mudar para filename ... e pegar o app_name via androguard
        # esse nome esta guardando o filename e nao o nome do app
        self.name = os.path.basename(app_path)

        self.apk = APK(self.path)
        self.package_name = self.apk.get_package()
        self.sdk_target = self.apk.get_effective_target_sdk_version()
        self.permissions = self.apk.get_permissions()
        self.min_api = self.apk.get_min_sdk_version()
