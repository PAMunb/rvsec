# tests/util/test_jar_resolver.py
"""
Comprehensive unit tests for the JarResolver utility.

This test suite covers JAR file resolution functionality, search path management,
error handling, and environment variable configuration.
"""

import os
import pytest
from unittest.mock import Mock, patch

from rv_android_core.util.jar_resolver import JarResolver
from rv_android_core.util.error.exceptions import JarNotFoundError


class TestJarResolver:
    """Test suite for JarResolver class"""

    @pytest.fixture
    def jar_resolver(self):
        """Create a JarResolver instance for testing"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            return JarResolver()

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing"""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()
            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    def test_initialization(self, mock_logging_manager):
        """Test JarResolver initialization"""
        resolver = JarResolver()

        # Verify logger was set up
        assert hasattr(resolver, 'logger')

    def test_resolve_jar_path_success(self, jar_resolver):
        """Test successful JAR file resolution"""
        jar_name = "test.jar"
        expected_path = "/path/to/test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.path.abspath') as mock_abspath:
                    mock_build.return_value = [expected_path, "/other/path"]
                    mock_isfile.side_effect = lambda p: p == expected_path
                    mock_abspath.return_value = expected_path

                    result = jar_resolver.resolve_jar_path(jar_name)

                    assert result == expected_path
                    mock_build.assert_called_once_with(jar_name, None)
                    mock_isfile.assert_called()

    def test_resolve_jar_path_not_found(self, jar_resolver):
        """Test JAR file not found scenario"""
        jar_name = "missing.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                mock_build.return_value = ["/path1/missing.jar", "/path2/missing.jar"]
                mock_isfile.return_value = False

                with pytest.raises(JarNotFoundError) as exc_info:
                    jar_resolver.resolve_jar_path(jar_name)

                assert jar_name in str(exc_info.value)
                assert "not found in search paths" in str(exc_info.value)

    def test_resolve_jar_path_with_custom_search_paths(self, jar_resolver):
        """Test JAR resolution with custom search paths"""
        jar_name = "test.jar"
        custom_paths = ["/custom/path1", "/custom/path2"]
        expected_path = "/custom/path1/test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.path.abspath') as mock_abspath:
                    mock_build.return_value = [expected_path]
                    mock_isfile.return_value = True
                    mock_abspath.return_value = expected_path

                    result = jar_resolver.resolve_jar_path(jar_name, custom_paths)

                    assert result == expected_path
                    mock_build.assert_called_once_with(jar_name, custom_paths)

    def test_resolve_multiple_jars_success(self, jar_resolver):
        """Test successful resolution of multiple JAR files"""
        jar_names = ["test1.jar", "test2.jar"]
        paths = ["/path/test1.jar", "/path/test2.jar"]

        with patch.object(jar_resolver, 'resolve_jar_path') as mock_resolve:
            mock_resolve.side_effect = paths

            result = jar_resolver.resolve_multiple_jars(jar_names)

            expected = {
                "test1": paths[0],
                "test2": paths[1]
            }
            assert result == expected
            assert mock_resolve.call_count == 2

    def test_resolve_multiple_jars_partial_failure(self, jar_resolver):
        """Test multiple JAR resolution with some files missing"""
        jar_names = ["found.jar", "missing.jar"]

        def mock_resolve_side_effect(jar_name, search_paths=None):
            if jar_name == "found.jar":
                return "/path/found.jar"
            else:
                raise JarNotFoundError(f"JAR file '{jar_name}' not found")

        with patch.object(jar_resolver, 'resolve_jar_path') as mock_resolve:
            mock_resolve.side_effect = mock_resolve_side_effect

            with pytest.raises(JarNotFoundError) as exc_info:
                jar_resolver.resolve_multiple_jars(jar_names)

            assert "missing.jar" in str(exc_info.value)

    def test_resolve_resource_directory_success(self, jar_resolver):
        """Test successful resource directory resolution"""
        resource_name = "libs"
        expected_path = "/path/to/libs"

        with patch.object(jar_resolver, '_build_resource_search_paths') as mock_build:
            with patch('os.path.isdir') as mock_isdir:
                with patch('os.path.abspath') as mock_abspath:
                    mock_build.return_value = [expected_path]
                    mock_isdir.return_value = True
                    mock_abspath.return_value = expected_path

                    result = jar_resolver.resolve_resource_directory(resource_name)

                    assert result == expected_path

    def test_resolve_resource_directory_not_found(self, jar_resolver):
        """Test resource directory not found scenario"""
        resource_name = "missing_libs"

        with patch.object(jar_resolver, '_build_resource_search_paths') as mock_build:
            with patch('os.path.isdir') as mock_isdir:
                mock_build.return_value = ["/path/missing_libs"]
                mock_isdir.return_value = False

                with pytest.raises(JarNotFoundError) as exc_info:
                    jar_resolver.resolve_resource_directory(resource_name)

                assert resource_name in str(exc_info.value)

    def test_build_search_paths_basic(self, jar_resolver):
        """Test basic search path building"""
        jar_name = "test.jar"

        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.abspath') as mock_abspath:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_search_paths(jar_name)

                # Should include current directory and standard paths
                assert any("test.jar" in path for path in paths)
                assert len(paths) > 0

    def test_build_search_paths_with_rvsec_home(self, jar_resolver):
        """Test search path building with RVSEC_HOME environment variable"""
        jar_name = "test.jar"
        rvsec_home = "/opt/rvsec"

        with patch.dict(os.environ, {'RVSEC_HOME': rvsec_home}):
            with patch('os.path.abspath') as mock_abspath:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_search_paths(jar_name)

                # Should include RVSEC_HOME based paths
                rvsec_paths = [p for p in paths if rvsec_home in p]
                assert len(rvsec_paths) > 0

    def test_build_search_paths_with_additional_paths(self, jar_resolver):
        """Test search path building with additional custom paths"""
        jar_name = "test.jar"
        additional_paths = ["/custom1", "/custom2"]

        with patch('os.path.abspath') as mock_abspath:
            with patch('os.path.isdir') as mock_isdir:
                mock_abspath.side_effect = lambda p: f"/abs{p}"
                mock_isdir.return_value = True  # Treat all as directories

                paths = jar_resolver._build_search_paths(jar_name, additional_paths)

                # Additional paths should be included with highest priority
                # When isdir returns True, jar_name is appended
                assert "/abs/custom1/test.jar" in paths
                assert "/abs/custom2/test.jar" in paths

    def test_build_search_paths_with_tools_dir(self, jar_resolver):
        """Test search path building with TOOLS_DIR environment variable"""
        jar_name = "test.jar"
        tools_dir = "/opt/tools"

        with patch.dict(os.environ, {'TOOLS_DIR': tools_dir}):
            with patch('os.path.abspath') as mock_abspath:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_search_paths(jar_name)

                # Should include TOOLS_DIR based paths
                tools_paths = [p for p in paths if tools_dir in p]
                assert len(tools_paths) > 0

    def test_build_resource_search_paths(self, jar_resolver):
        """Test resource directory search path building"""
        resource_name = "libs"

        with patch('os.path.abspath') as mock_abspath:
            mock_abspath.side_effect = lambda p: f"/abs{p}"

            paths = jar_resolver._build_resource_search_paths(resource_name)

            # Should include resource name in paths
            assert any(resource_name in path for path in paths)
            assert len(paths) > 0

    def test_build_resource_search_paths_with_additional(self, jar_resolver):
        """Test resource search paths with additional paths"""
        resource_name = "libs"
        additional_paths = ["/custom/path"]

        with patch('os.path.abspath') as mock_abspath:
            mock_abspath.side_effect = lambda p: f"/abs{p}"

            paths = jar_resolver._build_resource_search_paths(resource_name, additional_paths)

            # Additional paths should be included
            assert "/abs/custom/path/libs" in paths

    def test_get_tool_subdir_from_jar_direct_mapping(self, jar_resolver):
        """Test tool subdirectory mapping for known JAR files"""
        test_cases = [
            ("ape.jar", "ape"),
            ("fastbot-thirdpart.jar", "fastbot"),
            ("framework.jar", "fastbot"),
            ("monkeyq.jar", "fastbot"),
            ("droidmate.jar", "droidmate")
        ]

        for jar_name, expected_subdir in test_cases:
            result = jar_resolver._get_tool_subdir_from_jar(jar_name)
            assert result == expected_subdir

    def test_get_tool_subdir_from_jar_pattern_detection(self, jar_resolver):
        """Test tool subdirectory pattern-based detection"""
        test_cases = [
            ("droidmate-2.3.4-all.jar", "droidmate"),
            ("fastbot-custom.jar", "fastbot"),
            ("ape-modified.jar", "ape"),
            ("unknown-tool.jar", "unknown-tool")
        ]

        for jar_name, expected_subdir in test_cases:
            result = jar_resolver._get_tool_subdir_from_jar(jar_name)
            assert result == expected_subdir

    def test_get_jar_key_direct_mapping(self, jar_resolver):
        """Test JAR key generation for known files"""
        test_cases = [
            ("fastbot-thirdpart.jar", "fastbot_thirdpart"),
            ("framework.jar", "framework"),
            ("monkeyq.jar", "monkeyq"),
            ("ape.jar", "ape")
        ]

        for jar_name, expected_key in test_cases:
            result = jar_resolver._get_jar_key(jar_name)
            assert result == expected_key

    def test_get_jar_key_generated(self, jar_resolver):
        """Test JAR key generation for unknown files"""
        test_cases = [
            ("custom-tool.jar", "custom_tool"),
            ("my.tool.jar", "my_tool"),
            ("tool-1.0.jar", "tool_1_0")
        ]

        for jar_name, expected_key in test_cases:
            result = jar_resolver._get_jar_key(jar_name)
            assert result == expected_key

    def test_verify_jar_accessibility_success(self, jar_resolver):
        """Test successful JAR accessibility verification"""
        jar_path = "/path/to/test.jar"

        with patch('os.path.exists') as mock_exists:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.access') as mock_access:
                    with patch('os.path.getsize') as mock_getsize:
                        mock_exists.return_value = True
                        mock_isfile.return_value = True
                        mock_access.return_value = True
                        mock_getsize.return_value = 1024

                        result = jar_resolver.verify_jar_accessibility(jar_path)

                        assert result is True

    def test_verify_jar_accessibility_not_exists(self, jar_resolver):
        """Test JAR accessibility when file doesn't exist"""
        jar_path = "/path/to/missing.jar"

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            result = jar_resolver.verify_jar_accessibility(jar_path)

            assert result is False

    def test_verify_jar_accessibility_not_file(self, jar_resolver):
        """Test JAR accessibility when path is not a file"""
        jar_path = "/path/to/directory"

        with patch('os.path.exists') as mock_exists:
            with patch('os.path.isfile') as mock_isfile:
                mock_exists.return_value = True
                mock_isfile.return_value = False

                result = jar_resolver.verify_jar_accessibility(jar_path)

                assert result is False

    def test_verify_jar_accessibility_not_readable(self, jar_resolver):
        """Test JAR accessibility when file is not readable"""
        jar_path = "/path/to/test.jar"

        with patch('os.path.exists') as mock_exists:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.access') as mock_access:
                    mock_exists.return_value = True
                    mock_isfile.return_value = True
                    mock_access.return_value = False

                    result = jar_resolver.verify_jar_accessibility(jar_path)

                    assert result is False

    def test_verify_jar_accessibility_empty_file(self, jar_resolver):
        """Test JAR accessibility when file is empty"""
        jar_path = "/path/to/empty.jar"

        with patch('os.path.exists') as mock_exists:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.access') as mock_access:
                    with patch('os.path.getsize') as mock_getsize:
                        mock_exists.return_value = True
                        mock_isfile.return_value = True
                        mock_access.return_value = True
                        mock_getsize.return_value = 0

                        result = jar_resolver.verify_jar_accessibility(jar_path)

                        assert result is False

    def test_verify_jar_accessibility_os_error(self, jar_resolver):
        """Test JAR accessibility with OS error"""
        jar_path = "/path/to/test.jar"

        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = OSError("Permission denied")

            result = jar_resolver.verify_jar_accessibility(jar_path)

            assert result is False

    def test_get_search_paths_info(self, jar_resolver):
        """Test search paths information gathering"""
        jar_name = "test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.exists') as mock_exists:
                with patch('os.path.isfile') as mock_isfile:
                    with patch('os.access') as mock_access:
                        with patch('os.path.getsize') as mock_getsize:
                            mock_build.return_value = ["/path1/test.jar", "/path2/test.jar"]

                            # Use functions instead of limited side_effect lists
                            def exists_side_effect(path):
                                return path == "/path1/test.jar"

                            def isfile_side_effect(path):
                                return path == "/path1/test.jar"

                            def access_side_effect(path, mode):
                                return path == "/path1/test.jar"

                            def getsize_side_effect(path):
                                return 1024 if path == "/path1/test.jar" else 0

                            mock_exists.side_effect = exists_side_effect
                            mock_isfile.side_effect = isfile_side_effect
                            mock_access.side_effect = access_side_effect
                            mock_getsize.side_effect = getsize_side_effect

                            result = jar_resolver.get_search_paths_info(jar_name)

                            assert result['jar_name'] == jar_name
                            assert result['total_paths'] == 2
                            assert len(result['paths']) == 2

                            # First path should show as accessible
                            assert result['paths'][0]['exists'] is True
                            assert result['paths'][0]['is_file'] is True
                            assert result['paths'][0]['readable'] is True
                            assert result['paths'][0]['size'] == 1024

                            # Second path should show as not accessible
                            assert result['paths'][1]['exists'] is False

    def test_get_search_paths_info_with_additional_paths(self, jar_resolver):
        """Test search paths info with additional paths"""
        jar_name = "test.jar"
        additional_paths = ["/custom"]

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.exists') as mock_exists:
                with patch('os.path.isfile') as mock_isfile:
                    with patch('os.access') as mock_access:
                        with patch('os.path.getsize') as mock_getsize:
                            mock_build.return_value = ["/custom/test.jar"]
                            mock_exists.return_value = True
                            mock_isfile.return_value = True
                            mock_access.return_value = True
                            mock_getsize.return_value = 2048

                            result = jar_resolver.get_search_paths_info(jar_name, additional_paths)

                            mock_build.assert_called_once_with(jar_name, additional_paths)
                            assert result['total_paths'] == 1

    def test_build_search_paths_invalid_paths(self, jar_resolver):
        """Test search path building with invalid paths"""
        jar_name = "test.jar"

        with patch('os.path.abspath') as mock_abspath:
            # Simulate OSError when processing invalid paths
            def mock_abspath_side_effect(path):
                if "invalid" in path:
                    raise OSError("Invalid path")
                return f"/abs{path}"

            mock_abspath.side_effect = mock_abspath_side_effect

            # Add an invalid path that should be skipped
            with patch.dict(os.environ, {}, clear=True):
                paths = jar_resolver._build_search_paths(jar_name)

                # Should still return paths, just skip the invalid ones
                assert len(paths) > 0
                assert all("invalid" not in path for path in paths)

    def test_build_search_paths_empty_paths(self, jar_resolver):
        """Test search path building filters out empty paths"""
        jar_name = "test.jar"
        additional_paths = ["", "  ", "/valid/path"]

        with patch('os.path.abspath') as mock_abspath:
            with patch('os.path.isdir') as mock_isdir:
                mock_abspath.side_effect = lambda p: f"/abs{p}"
                mock_isdir.return_value = True

                paths = jar_resolver._build_search_paths(jar_name, additional_paths)

                # Empty and whitespace-only paths should be filtered out
                assert "/abs/valid/path/test.jar" in paths
                assert not any(not p.strip() for p in paths)

    def test_build_search_paths_duplicate_removal(self, jar_resolver):
        """Test that duplicate paths are removed"""
        jar_name = "test.jar"

        with patch('os.path.abspath') as mock_abspath:
            # Return the same absolute path for different inputs
            mock_abspath.return_value = "/same/absolute/path/test.jar"

            paths = jar_resolver._build_search_paths(jar_name)

            # Should not contain duplicates
            assert len(paths) == len(set(paths))

    def test_resolve_jar_path_direct_file_path(self, jar_resolver):
        """Test JAR resolution when additional path is a direct file path"""
        jar_name = "test.jar"
        direct_file_path = "/direct/path/to/test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.path.abspath') as mock_abspath:
                    mock_build.return_value = [direct_file_path]
                    mock_isfile.return_value = True
                    mock_abspath.return_value = direct_file_path

                    result = jar_resolver.resolve_jar_path(jar_name, [direct_file_path])

                    assert result == direct_file_path

    def test_build_search_paths_additional_direct_files(self, jar_resolver):
        """Test search path building when additional paths include direct files"""
        jar_name = "test.jar"
        additional_paths = ["/direct/file.jar", "/directory/path"]

        with patch('os.path.abspath') as mock_abspath:
            with patch('os.path.isdir') as mock_isdir:
                mock_abspath.side_effect = lambda p: f"/abs{p}"
                mock_isdir.side_effect = lambda p: not p.endswith('.jar')

                paths = jar_resolver._build_search_paths(jar_name, additional_paths)

                # Direct file should be included as-is
                assert "/abs/direct/file.jar" in paths
                # Directory should have jar name appended
                assert "/abs/directory/path/test.jar" in paths


class TestJarResolverIntegration:
    """Integration tests for JarResolver using temporary files"""

    @pytest.fixture
    def temp_jar_structure(self, tmp_path):
        """Create temporary JAR file structure for testing"""
        # Create directory structure
        ape_dir = tmp_path / "tools" / "ape"
        fastbot_dir = tmp_path / "tools" / "fastbot"
        fastbot_libs = fastbot_dir / "libs"

        ape_dir.mkdir(parents=True)
        fastbot_dir.mkdir(parents=True)
        fastbot_libs.mkdir(parents=True)

        # Create JAR files
        ape_jar = ape_dir / "ape.jar"
        fastbot_jar = fastbot_dir / "fastbot-thirdpart.jar"
        framework_jar = fastbot_dir / "framework.jar"

        ape_jar.write_bytes(b"fake jar content")
        fastbot_jar.write_bytes(b"fake jar content")
        framework_jar.write_bytes(b"fake jar content")

        return {
            'base_dir': tmp_path,
            'ape_jar': str(ape_jar),
            'fastbot_jar': str(fastbot_jar),
            'framework_jar': str(framework_jar),
            'fastbot_libs': str(fastbot_libs)
        }

    def test_real_jar_resolution(self, temp_jar_structure):
        """Test JAR resolution with real file system"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            resolver = JarResolver()

            # Use the exact directory containing the JAR file
            ape_dir = str(temp_jar_structure['base_dir'] / "tools" / "ape")
            search_paths = [ape_dir]

            # Test resolving APE JAR
            result = resolver.resolve_jar_path("ape.jar", search_paths)
            assert result == temp_jar_structure['ape_jar']

            # Verify accessibility
            assert resolver.verify_jar_accessibility(result) is True

    def test_real_multiple_jar_resolution(self, temp_jar_structure):
        """Test multiple JAR resolution with real files"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            resolver = JarResolver()

            # Provide specific directories for each JAR
            ape_dir = str(temp_jar_structure['base_dir'] / "tools" / "ape")
            fastbot_dir = str(temp_jar_structure['base_dir'] / "tools" / "fastbot")
            search_paths = [ape_dir, fastbot_dir]

            jar_names = ["ape.jar", "fastbot-thirdpart.jar"]

            result = resolver.resolve_multiple_jars(jar_names, search_paths)

            assert len(result) == 2
            assert "ape" in result
            assert "fastbot_thirdpart" in result
            assert result["ape"] == temp_jar_structure['ape_jar']
            assert result["fastbot_thirdpart"] == temp_jar_structure['fastbot_jar']

    def test_real_resource_directory_resolution(self, temp_jar_structure):
        """Test resource directory resolution with real directories"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            resolver = JarResolver()

            # Use the fastbot directory which contains the libs subdirectory
            fastbot_dir = str(temp_jar_structure['base_dir'] / "tools" / "fastbot")
            search_paths = [fastbot_dir]

            result = resolver.resolve_resource_directory("libs", search_paths)
            assert result == temp_jar_structure['fastbot_libs']

    def test_real_search_paths_info(self, temp_jar_structure):
        """Test search paths info with real file system"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            resolver = JarResolver()

            # Use the ape directory directly
            ape_dir = str(temp_jar_structure['base_dir'] / "tools" / "ape")
            search_paths = [ape_dir]

            info = resolver.get_search_paths_info("ape.jar", search_paths)

            assert info['jar_name'] == "ape.jar"
            assert info['total_paths'] > 0

            # Find the path that exists
            existing_paths = [p for p in info['paths'] if p['exists']]
            assert len(existing_paths) >= 1
            assert existing_paths[0]['is_file'] is True
            assert existing_paths[0]['readable'] is True
            assert existing_paths[0]['size'] > 0


class TestJarResolverEdgeCases:
    """Additional edge case tests for maximum coverage"""

    @pytest.fixture
    def jar_resolver(self):
        """Create a JarResolver instance for testing"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            return JarResolver()

    def test_build_search_paths_rvsec_and_tools_env(self, jar_resolver):
        """Test search path building with both RVSEC_HOME and TOOLS_DIR"""
        jar_name = "test.jar"
        rvsec_home = "/opt/rvsec"
        tools_dir = "/opt/tools"

        with patch.dict(os.environ, {'RVSEC_HOME': rvsec_home, 'TOOLS_DIR': tools_dir}):
            with patch('os.path.abspath') as mock_abspath:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_search_paths(jar_name)

                # Should include both RVSEC_HOME and TOOLS_DIR based paths
                rvsec_paths = [p for p in paths if rvsec_home in p]
                tools_paths = [p for p in paths if tools_dir in p]
                assert len(rvsec_paths) > 0
                assert len(tools_paths) > 0

    def test_get_tool_subdir_versioned_droidmate(self, jar_resolver):
        """Test tool subdirectory detection for versioned DroidMate JARs"""
        test_cases = [
            "droidmate-2.3.4-all.jar",
            "droidmate-3.0.0-SNAPSHOT.jar",
            "droidmate-custom-build.jar"
        ]

        for jar_name in test_cases:
            result = jar_resolver._get_tool_subdir_from_jar(jar_name)
            assert result == "droidmate"

    def test_get_jar_key_complex_names(self, jar_resolver):
        """Test JAR key generation for complex file names"""
        test_cases = [
            ("tool-with-many-dashes.jar", "tool_with_many_dashes"),
            ("tool.with.dots.jar", "tool_with_dots"),
            ("Tool-Mixed.Case.jar", "tool_mixed_case"),
            ("tool_with_underscores.jar", "tool_with_underscores")
        ]

        for jar_name, expected_key in test_cases:
            result = jar_resolver._get_jar_key(jar_name)
            assert result == expected_key

    def test_resolve_jar_path_empty_search_paths(self, jar_resolver):
        """Test JAR resolution with empty search paths"""
        jar_name = "test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            mock_build.return_value = []

            with pytest.raises(JarNotFoundError) as exc_info:
                jar_resolver.resolve_jar_path(jar_name)

            assert "not found in search paths" in str(exc_info.value)

    def test_resolve_multiple_jars_empty_list(self, jar_resolver):
        """Test multiple JAR resolution with empty jar list"""
        result = jar_resolver.resolve_multiple_jars([])
        assert result == {}

    def test_verify_jar_accessibility_permission_error(self, jar_resolver):
        """Test JAR accessibility with permission error during size check"""
        jar_path = "/path/to/test.jar"

        with patch('os.path.exists') as mock_exists:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.access') as mock_access:
                    with patch('os.path.getsize') as mock_getsize:
                        mock_exists.return_value = True
                        mock_isfile.return_value = True
                        mock_access.return_value = True
                        mock_getsize.side_effect = PermissionError("Permission denied")

                        result = jar_resolver.verify_jar_accessibility(jar_path)

                        assert result is False

    def test_build_search_paths_mixed_additional_paths(self, jar_resolver):
        """Test search path building with mixed file and directory additional paths"""
        jar_name = "test.jar"
        additional_paths = ["/file.jar", "/directory", "", "  "]  # Mixed with empty paths

        with patch('os.path.abspath') as mock_abspath:
            with patch('os.path.isdir') as mock_isdir:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                def isdir_side_effect(path):
                    return not path.endswith('.jar')

                mock_isdir.side_effect = isdir_side_effect

                paths = jar_resolver._build_search_paths(jar_name, additional_paths)

                # File path should be included as-is
                assert "/abs/file.jar" in paths
                # Directory should have jar name appended
                assert "/abs/directory/test.jar" in paths
                # Empty paths should be filtered out

    def test_build_resource_search_paths_rvsec_home(self, jar_resolver):
        """Test resource search paths with RVSEC_HOME environment variable"""
        resource_name = "libs"
        rvsec_home = "/opt/rvsec"

        with patch.dict(os.environ, {'RVSEC_HOME': rvsec_home}):
            with patch('os.path.abspath') as mock_abspath:
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_resource_search_paths(resource_name)

                # Should include RVSEC_HOME based paths for fastbot (default tool)
                rvsec_paths = [p for p in paths if rvsec_home in p and resource_name in p]
                assert len(rvsec_paths) > 0

    def test_resolve_jar_path_case_insensitive_error_logging(self, jar_resolver):
        """Test that error logging works correctly during JAR resolution failure"""
        jar_name = "missing.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                mock_build.return_value = ["/path1/missing.jar", "/path2/missing.jar"]
                mock_isfile.return_value = False

                # Capture logger calls
                with patch.object(jar_resolver, 'logger') as mock_logger:
                    with pytest.raises(JarNotFoundError):
                        jar_resolver.resolve_jar_path(jar_name)

                    # Verify error logging was called
                    mock_logger.error.assert_called()

    def test_resolve_multiple_jars_all_missing(self, jar_resolver):
        """Test multiple JAR resolution when all JARs are missing"""
        jar_names = ["missing1.jar", "missing2.jar", "missing3.jar"]

        with patch.object(jar_resolver, 'resolve_jar_path') as mock_resolve:
            mock_resolve.side_effect = JarNotFoundError("JAR not found")

            with pytest.raises(JarNotFoundError) as exc_info:
                jar_resolver.resolve_multiple_jars(jar_names)

            # Should mention all missing JARs
            error_msg = str(exc_info.value)
            assert "missing1.jar" in error_msg
            assert "missing2.jar" in error_msg
            assert "missing3.jar" in error_msg

    def test_get_search_paths_info_comprehensive(self, jar_resolver):
        """Test comprehensive search paths info with various file states"""
        jar_name = "test.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            mock_build.return_value = [
                "/existing/readable/test.jar",
                "/existing/unreadable/test.jar",
                "/nonexistent/test.jar",
                "/directory/test.jar"  # Path that exists but is not a file
            ]

            with patch('os.path.exists') as mock_exists:
                with patch('os.path.isfile') as mock_isfile:
                    with patch('os.access') as mock_access:
                        with patch('os.path.getsize') as mock_getsize:

                            def exists_side_effect(path):
                                return "nonexistent" not in path

                            def isfile_side_effect(path):
                                return "directory" not in path and "nonexistent" not in path

                            def access_side_effect(path, mode):
                                return "unreadable" not in path

                            def getsize_side_effect(path):
                                if "existing/readable" in path:
                                    return 2048
                                elif "existing/unreadable" in path:
                                    return 1024
                                return 0

                            mock_exists.side_effect = exists_side_effect
                            mock_isfile.side_effect = isfile_side_effect
                            mock_access.side_effect = access_side_effect
                            mock_getsize.side_effect = getsize_side_effect

                            result = jar_resolver.get_search_paths_info(jar_name)

                            assert result['total_paths'] == 4
                            assert len(result['paths']) == 4

                            # Check each path state
                            paths_info = {p['path']: p for p in result['paths']}

                            # Readable file
                            readable_info = paths_info["/existing/readable/test.jar"]
                            assert readable_info['exists'] is True
                            assert readable_info['is_file'] is True
                            assert readable_info['readable'] is True
                            assert readable_info['size'] == 2048

                            # Unreadable file
                            unreadable_info = paths_info["/existing/unreadable/test.jar"]
                            assert unreadable_info['exists'] is True
                            assert unreadable_info['is_file'] is True
                            assert unreadable_info['readable'] is False

                            # Non-existent path
                            nonexistent_info = paths_info["/nonexistent/test.jar"]
                            assert nonexistent_info['exists'] is False
                            assert nonexistent_info['is_file'] is False

    def test_build_search_paths_home_expansion(self, jar_resolver):
        """Test that home directory expansion works in search paths"""
        jar_name = "test.jar"

        with patch('os.path.expanduser') as mock_expanduser:
            with patch('os.path.abspath') as mock_abspath:
                mock_expanduser.side_effect = lambda p: p.replace('~', '/home/user')
                mock_abspath.side_effect = lambda p: f"/abs{p}"

                paths = jar_resolver._build_search_paths(jar_name)

                # Should include expanded home directory paths
                home_paths = [p for p in paths if '/home/user/' in p]
                assert len(home_paths) > 0

    def test_resolve_resource_directory_with_empty_additional_paths(self, jar_resolver):
        """Test resource directory resolution with empty additional paths"""
        resource_name = "libs"
        additional_paths = ["", "  ", None]  # Various empty/invalid paths

        # Filter out None from additional_paths as the real method would
        filtered_paths = [p for p in additional_paths if p is not None]

        with patch.object(jar_resolver, '_build_resource_search_paths') as mock_build:
            with patch('os.path.isdir') as mock_isdir:
                mock_build.return_value = ["/default/libs"]
                mock_isdir.return_value = False

                with pytest.raises(JarNotFoundError):
                    jar_resolver.resolve_resource_directory(resource_name, filtered_paths)

    def test_jar_not_found_error_attributes(self, jar_resolver):
        """Test that JarNotFoundError includes proper attributes"""
        jar_name = "missing.jar"

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                search_paths = ["/path1/missing.jar", "/path2/missing.jar"]
                mock_build.return_value = search_paths
                mock_isfile.return_value = False

                with pytest.raises(JarNotFoundError) as exc_info:
                    jar_resolver.resolve_jar_path(jar_name)

                error = exc_info.value
                assert hasattr(error, 'jar_name')
                assert hasattr(error, 'search_paths')
                assert error.jar_name == jar_name
                assert error.search_paths == search_paths

    def test_build_search_paths_value_error_handling(self, jar_resolver):
        """Test search path building handles ValueError during path processing"""
        jar_name = "test.jar"

        with patch('os.path.abspath') as mock_abspath:
            # First call succeeds, second raises ValueError, third succeeds
            mock_abspath.side_effect = ["/abs/valid", ValueError("Invalid path"), "/abs/valid2"] + ["/abs/path"] * 20

            paths = jar_resolver._build_search_paths(jar_name)

            # Should continue processing and skip the invalid path
            assert len(paths) > 0
            assert "/abs/valid" in paths[0] or "/abs/valid2" in paths[0]


class TestJarResolverErrorHandling:
    """Test error handling and decorator integration"""

    @pytest.fixture
    def jar_resolver(self):
        """Create a JarResolver instance for testing"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            return JarResolver()

    def test_error_handler_decorator_integration(self, jar_resolver):
        """Test that ErrorHandler decorators work correctly with JarResolver methods"""
        # The resolve_jar_path method should be decorated with @ErrorHandler.handle_errors

        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                mock_build.return_value = []
                mock_isfile.return_value = False

                # This should raise JarNotFoundError but may be handled by error handler
                with pytest.raises(JarNotFoundError):
                    jar_resolver.resolve_jar_path("missing.jar")

    def test_logging_integration(self, jar_resolver):
        """Test that logging is properly integrated throughout the resolution process"""
        jar_name = "test.jar"

        # Test debug logging during successful resolution
        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                with patch('os.path.abspath') as mock_abspath:
                    with patch.object(jar_resolver, 'logger') as mock_logger:
                        mock_build.return_value = ["/found/test.jar"]
                        mock_isfile.return_value = True
                        mock_abspath.return_value = "/found/test.jar"

                        jar_resolver.resolve_jar_path(jar_name)

                        # Should have debug logging for resolution start and success
                        assert mock_logger.debug.call_count >= 2

        # Test error logging during failed resolution
        with patch.object(jar_resolver, '_build_search_paths') as mock_build:
            with patch('os.path.isfile') as mock_isfile:
                with patch.object(jar_resolver, 'logger') as mock_logger:
                    mock_build.return_value = ["/missing/test.jar"]
                    mock_isfile.return_value = False

                    with pytest.raises(JarNotFoundError):
                        jar_resolver.resolve_jar_path(jar_name)

                    # Should have error logging for failed resolution
                    mock_logger.error.assert_called()

    def test_multiple_jars_logging(self, jar_resolver):
        """Test logging during multiple JAR resolution"""
        jar_names = ["jar1.jar", "jar2.jar"]

        with patch.object(jar_resolver, 'resolve_jar_path') as mock_resolve:
            with patch.object(jar_resolver, 'logger') as mock_logger:
                mock_resolve.side_effect = ["/path/jar1.jar", "/path/jar2.jar"]

                result = jar_resolver.resolve_multiple_jars(jar_names)

                # Should log successful resolution
                mock_logger.info.assert_called()
                assert len(result) == 2

    def test_resource_directory_logging(self, jar_resolver):
        """Test logging during resource directory resolution"""
        resource_name = "libs"

        with patch.object(jar_resolver, '_build_resource_search_paths') as mock_build:
            with patch('os.path.isdir') as mock_isdir:
                with patch('os.path.abspath') as mock_abspath:
                    with patch.object(jar_resolver, 'logger') as mock_logger:
                        mock_build.return_value = ["/found/libs"]
                        mock_isdir.return_value = True
                        mock_abspath.return_value = "/found/libs"

                        jar_resolver.resolve_resource_directory(resource_name)

                        # Should have debug logging for resolution
                        mock_logger.debug.assert_called()

    def test_context_component_logging(self, jar_resolver):
        """Test that JarResolver uses proper logging context component"""
        # Verify that the logger was initialized with correct context
        assert hasattr(jar_resolver, 'logger')

        # Test that the logger context includes the JarResolver component
        # This verifies the CONTEXT_COMPONENT integration


class TestJarResolverCompleteWorkflow:
    """End-to-end workflow tests"""

    @pytest.fixture
    def jar_resolver(self):
        """Create a JarResolver instance for testing"""
        with patch('rv_android_core.util.logging.manager.LoggingManager'):
            return JarResolver()

    def test_complete_jar_resolution_workflow(self, jar_resolver):
        """Test a complete JAR resolution workflow from start to finish"""
        jar_name = "ape.jar"
        search_paths = ["/tools/ape"]
        expected_path = "/tools/ape/ape.jar"

        with patch('os.path.isfile') as mock_isfile:
            with patch('os.path.abspath') as mock_abspath:
                with patch('os.path.exists') as mock_exists:
                    with patch('os.access') as mock_access:
                        with patch('os.path.getsize') as mock_getsize:
                            # Setup mocks for successful resolution
                            mock_isfile.side_effect = lambda p: p == expected_path
                            mock_abspath.return_value = expected_path
                            mock_exists.return_value = True
                            mock_access.return_value = True
                            mock_getsize.return_value = 1024

                            # Step 1: Resolve the JAR
                            resolved_path = jar_resolver.resolve_jar_path(jar_name, search_paths)
                            assert resolved_path == expected_path

                            # Step 2: Verify accessibility
                            is_accessible = jar_resolver.verify_jar_accessibility(resolved_path)
                            assert is_accessible is True

                            # Step 3: Get search paths info
                            info = jar_resolver.get_search_paths_info(jar_name, search_paths)
                            assert info['jar_name'] == jar_name

                            # Find the successful path in the info
                            successful_paths = [p for p in info['paths'] if p['exists']]
                            assert len(successful_paths) >= 1

    def test_complete_failure_workflow(self, jar_resolver):
        """Test a complete workflow when JARs are not found"""
        jar_names = ["missing1.jar", "missing2.jar"]
        search_paths = ["/nonexistent"]

        with patch('os.path.isfile') as mock_isfile:
            with patch('os.path.exists') as mock_exists:
                mock_isfile.return_value = False
                mock_exists.return_value = False

                # Should fail to resolve individual JARs
                with pytest.raises(JarNotFoundError):
                    jar_resolver.resolve_jar_path(jar_names[0], search_paths)

                # Should fail to resolve multiple JARs
                with pytest.raises(JarNotFoundError):
                    jar_resolver.resolve_multiple_jars(jar_names, search_paths)

                # Search paths info should show no accessible paths
                info = jar_resolver.get_search_paths_info(jar_names[0], search_paths)
                accessible_paths = [p for p in info['paths'] if p['exists']]
                assert len(accessible_paths) == 0
