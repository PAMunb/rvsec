"""Regression tests for PackageDetector manifest-vs-code matching (issue #63).

Covers two defects in the fast-path of ``detect_package()``:

- **Defect 1 — vacuous same_package**: an empty ``app_components`` list must NOT
  yield a high-confidence ``same_package`` result. With no application components
  the detector has no evidence, so it must fall through to the ``no_app_components``
  branch (``confidence="low"``).
- **Defect 2 — substring vs namespace matching**: the manifest package must match a
  component only when it is the same package or a true namespace prefix. A sibling
  package (``com.foobar`` vs manifest ``com.foo``) is a substring but NOT a
  namespace match and must not be treated as ``same_package``. A genuine
  sub-package (``com.foo.ui``) IS a namespace match and must stay ``same_package``.
"""

from rv_android_core.util.android.package_detector import PackageDetector


class _StubAPK:
    """Minimal androguard APK stand-in exposing only the accessors that
    ``detect_package()`` reads. ContentProviders are not consumed by the detector,
    so they are intentionally omitted."""

    def __init__(self, package, activities=None, services=None, receivers=None):
        self._package = package
        self._activities = activities or []
        self._services = services or []
        self._receivers = receivers or []

    def get_package(self):
        return self._package

    def get_activities(self):
        return self._activities

    def get_services(self):
        return self._services

    def get_receivers(self):
        return self._receivers


def test_empty_app_components_yields_low_confidence_no_app_components():
    """Defect 1: with no application components, detection must be low-confidence
    ``no_app_components`` — never a vacuous high-confidence ``same_package``."""
    apk = _StubAPK(package="com.foo")  # no activities/services/receivers

    result = PackageDetector().detect_package(apk)

    assert result.detection_method == "no_app_components"
    assert result.confidence == "low"


def test_sibling_package_is_not_same_package():
    """Defect 2: manifest ``com.foo`` must NOT match the sibling package
    ``com.foobar`` even though it is a substring."""
    apk = _StubAPK(package="com.foo", activities=["com.foobar.MainActivity"])

    result = PackageDetector().detect_package(apk)

    assert result.detection_method != "same_package"


def test_genuine_subpackage_is_same_package():
    """Defect 2 (positive case): manifest ``com.foo`` IS a namespace prefix of
    ``com.foo.ui.MainActivity``, so the result stays high-confidence
    ``same_package``."""
    apk = _StubAPK(package="com.foo", activities=["com.foo.ui.MainActivity"])

    result = PackageDetector().detect_package(apk)

    assert result.detection_method == "same_package"
    assert result.confidence == "high"
