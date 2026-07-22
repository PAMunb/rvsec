"""
Unit tests for rv_uiautomator.utils.screenshot_manager.

Tests cover ScreenshotManager path generation, image optimization (PNG →
compressed JPEG), validation, and disk-space cleanup. LoggingManager and PIL's
Image are mocked; filesystem operations run for real against pytest tmp_path.
No device/emulator/adb is ever touched (pure file/image processing).
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rv_uiautomator.utils.screenshot_manager import ScreenshotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_file(path, size):
    """Write a real file of exactly `size` zero bytes and return its Path."""
    p = Path(path)
    p.write_bytes(b"\0" * size)
    return p


def fake_image_cm(mode="RGB", size=(1080, 1920), converted=None, save_side_effect=None):
    """
    Build a fake PIL image supporting the `with Image.open(path) as img:` protocol.

    Returns (context_manager, img) so callers can wire it as
    Image.open.return_value = context_manager and later assert on `img`.
    """
    img = MagicMock()
    img.mode = mode
    img.size = size
    if converted is not None:
        img.convert.return_value = converted
    if save_side_effect is not None:
        img.save.side_effect = save_side_effect

    cm = MagicMock()
    cm.__enter__.return_value = img
    cm.__exit__.return_value = False
    return cm, img


def save_creates_file(*, size=2048):
    """A `.save(path, ...)` side_effect that actually writes a real file."""

    def _save(path, *args, **kwargs):
        Path(path).write_bytes(b"\0" * size)

    return _save


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shots_dir(tmp_path):
    """Directory string passed to ScreenshotManager (created by __init__)."""
    return str(tmp_path / "shots")


@pytest.fixture
def manager(shots_dir):
    """ScreenshotManager with LoggingManager patched so logger is a MagicMock."""
    with patch(
        "rv_uiautomator.utils.screenshot_manager.LoggingManager"
    ) as mock_lm:
        mock_logger = MagicMock()
        mock_lm.get_instance.return_value.get_logger.return_value = mock_logger
        mgr = ScreenshotManager(shots_dir)
    return mgr


# ---------------------------------------------------------------------------
# __init__ (53-64)
# ---------------------------------------------------------------------------


def test_init_creates_dir_and_wires_logger(manager, shots_dir):
    """__init__ stores the Path, creates the directory, and keeps the logger.

    Traceability: constructor contract (dir exists, logger available). The dir
    is created on disk (real mkdir against tmp_path).
    """
    assert manager.screenshot_dir == Path(shots_dir)
    assert manager.screenshot_dir.exists()
    assert isinstance(manager.logger, MagicMock)
    manager.logger.debug.assert_called_once()


# ---------------------------------------------------------------------------
# generate_screenshot_path (80-82)
#
# Boundary/equivalence over (prefix, extension): the default pair and a custom
# pair. time.time is pinned so the millisecond timestamp is deterministic.
# ---------------------------------------------------------------------------


def test_generate_screenshot_path_default(manager, shots_dir):
    """Default prefix/extension yields screenshot_<ms>.png under the dir."""
    with patch(
        "rv_uiautomator.utils.screenshot_manager.time.time", return_value=1234.5678
    ):
        result = manager.generate_screenshot_path()

    assert result == str(Path(shots_dir) / "screenshot_1234567.png")


def test_generate_screenshot_path_custom_prefix_extension(manager, shots_dir):
    """Custom prefix/extension are honoured in the generated filename."""
    with patch(
        "rv_uiautomator.utils.screenshot_manager.time.time", return_value=1234.5678
    ):
        result = manager.generate_screenshot_path(prefix="cap", extension="jpg")

    assert result == str(Path(shots_dir) / "cap_1234567.jpg")


# ---------------------------------------------------------------------------
# optimize_screenshot (100-128)
#
# Decision table over (file exists?) × (img.mode) × (save produced a file?) ×
# (Image.open raises?). The .png suffix is mandatory because the code derives
# the optimized/final paths via str.replace(".png", ...).
# ---------------------------------------------------------------------------


def test_optimize_screenshot_missing_file(manager, tmp_path):
    """Non-existent input short-circuits to False without opening PIL (101-103)."""
    missing = str(tmp_path / "shots" / "nope.png")
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        assert manager.optimize_screenshot(missing) is False
        mock_image.open.assert_not_called()


def test_optimize_screenshot_rgba_converts_and_replaces(manager, tmp_path):
    """RGBA image is converted to RGB, saved, original removed, renamed to .jpg (106-121)."""
    src = write_file(tmp_path / "shots" / "shot.png", 4096)

    # Converted image mock: its .save writes the optimized file.
    converted_img = MagicMock()
    converted_img.save.side_effect = save_creates_file()

    cm, img = fake_image_cm(mode="RGBA", converted=converted_img)

    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.return_value = cm
        result = manager.optimize_screenshot(str(src))

    assert result is True
    img.convert.assert_called_once_with("RGB")
    # Original .png removed; final .jpg produced by os.rename.
    assert not src.exists()
    assert (tmp_path / "shots" / "shot.jpg").exists()


def test_optimize_screenshot_rgb_skips_convert(manager, tmp_path):
    """RGB image is not converted; save creates the optimized file → True (108 false)."""
    src = write_file(tmp_path / "shots" / "shot.png", 4096)
    cm, img = fake_image_cm(mode="RGB", save_side_effect=save_creates_file())

    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.return_value = cm
        result = manager.optimize_screenshot(str(src))

    assert result is True
    img.convert.assert_not_called()
    assert not src.exists()
    assert (tmp_path / "shots" / "shot.jpg").exists()


def test_optimize_screenshot_save_produces_no_file(manager, tmp_path):
    """save succeeds but writes nothing → optimized path absent → False (116 false, 122)."""
    src = write_file(tmp_path / "shots" / "shot.png", 4096)
    # save is a no-op: does NOT create the optimized file.
    cm, img = fake_image_cm(mode="RGB", save_side_effect=lambda *a, **k: None)

    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.return_value = cm
        result = manager.optimize_screenshot(str(src))

    assert result is False
    # Original untouched (os.remove never reached).
    assert src.exists()


def test_optimize_screenshot_open_raises(manager, tmp_path):
    """Image.open raising is swallowed by the inner except → False (124-128)."""
    src = write_file(tmp_path / "shots" / "shot.png", 4096)
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.side_effect = OSError("cannot open image")
        assert manager.optimize_screenshot(str(src)) is False


# ---------------------------------------------------------------------------
# validate_screenshot (143-175)
#
# Basis-path over the guards: missing file → size guard → PIL dimension guard →
# happy path → exception. Boundary value: file size at the 1024-byte threshold
# and dimensions at the 100px threshold.
# ---------------------------------------------------------------------------


def test_validate_screenshot_missing_file(manager, tmp_path):
    """Non-existent path fails validation → False (147-149)."""
    missing = str(tmp_path / "shots" / "absent.png")
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        assert manager.validate_screenshot(missing) is False
        mock_image.open.assert_not_called()


def test_validate_screenshot_too_small(manager, tmp_path):
    """File under 1024 bytes is rejected before PIL is consulted (152-157)."""
    tiny = write_file(tmp_path / "shots" / "tiny.png", 100)
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        assert manager.validate_screenshot(str(tiny)) is False
        mock_image.open.assert_not_called()


def test_validate_screenshot_valid(manager, tmp_path):
    """>= 1024 bytes and dimensions >= 100px → True (160-169)."""
    ok = write_file(tmp_path / "shots" / "ok.png", 2048)
    cm, _ = fake_image_cm(size=(1080, 1920))
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.return_value = cm
        assert manager.validate_screenshot(str(ok)) is True


def test_validate_screenshot_dimensions_too_small(manager, tmp_path):
    """Sufficient bytes but sub-100px dimensions → False (162-166)."""
    ok = write_file(tmp_path / "shots" / "small_dims.png", 2048)
    cm, _ = fake_image_cm(size=(50, 50))
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.return_value = cm
        assert manager.validate_screenshot(str(ok)) is False


def test_validate_screenshot_open_raises(manager, tmp_path):
    """PIL raising during validation is swallowed → False (171-175)."""
    ok = write_file(tmp_path / "shots" / "boom.png", 2048)
    with patch("rv_uiautomator.utils.screenshot_manager.Image") as mock_image:
        mock_image.open.side_effect = ValueError("bad image")
        assert manager.validate_screenshot(str(ok)) is False


# ---------------------------------------------------------------------------
# cleanup_old_screenshots (190-219)
#
# Files are matched by glob("screenshot_*"). Age is derived from real mtime via
# os.utime, exercising the age threshold boundary (max_age_hours=24 → 86400s).
# ---------------------------------------------------------------------------


def test_cleanup_dir_missing(manager):
    """Absent screenshot_dir returns 0 immediately (191-192)."""
    import shutil

    shutil.rmtree(manager.screenshot_dir)
    assert not manager.screenshot_dir.exists()
    assert manager.cleanup_old_screenshots() == 0


def test_cleanup_removes_only_old(manager, tmp_path):
    """Files older than max_age are unlinked; recent ones survive (194-215)."""
    import time as _time

    old = write_file(tmp_path / "shots" / "screenshot_old", 10)
    new = write_file(tmp_path / "shots" / "screenshot_new", 10)

    past = _time.time() - 100000  # older than 24h (86400s)
    os.utime(old, (past, past))
    now = _time.time()
    os.utime(new, (now, now))

    removed = manager.cleanup_old_screenshots(max_age_hours=24)

    assert removed == 1
    assert not old.exists()
    assert new.exists()
    # cleanup_count > 0 info log path (212-213).
    manager.logger.info.assert_called_once()


def test_cleanup_per_file_exception_continues(manager, tmp_path):
    """unlink raising is caught per-file; count unchanged → 0 (199-210)."""
    import time as _time

    old = write_file(tmp_path / "shots" / "screenshot_old", 10)
    past = _time.time() - 100000
    os.utime(old, (past, past))

    with patch.object(
        Path, "unlink", side_effect=PermissionError("locked")
    ):
        removed = manager.cleanup_old_screenshots(max_age_hours=24)

    assert removed == 0
    # File still present (unlink failed) and warning logged.
    assert old.exists()
    manager.logger.warning.assert_called_once()


def test_cleanup_outer_exception(manager):
    """glob raising is swallowed by the outer except → 0 (217-219)."""
    fake_dir = MagicMock()
    fake_dir.exists.return_value = True
    fake_dir.glob.side_effect = RuntimeError("glob exploded")
    manager.screenshot_dir = fake_dir

    assert manager.cleanup_old_screenshots() == 0
    manager.logger.error.assert_called_once()
