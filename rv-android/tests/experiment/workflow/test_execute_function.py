# tests/experiment/workflow/test_execute_function.py
from unittest.mock import Mock, patch


# Fix: Import Configuration from the correct location


class TestExecuteFunction:
    """
    Tests for the standalone execute function in the experiment_controller module.

    These tests verify that the execute function correctly:
    - Retrieves configuration from the Configuration singleton
    - Loads tools from ToolRegistry
    - Creates and runs an ExperimentController with the right parameters
    """

    def test_execute_with_config(self):
        """Test the execute function using Configuration singleton."""
        # Mock the Configuration class and instance
        with patch('rvandroid.config.configuration.Configuration') as mock_config_cls:
            mock_config = Mock()
            mock_config_cls.get_instance.return_value = mock_config

            # Configure mock return values
            mock_config.get_int.return_value = 2
            mock_config.get_list.return_value = [60]
            mock_config.get_str.return_value = ""
            mock_config.get_bool.return_value = True

            # Mock ToolRegistry
            with patch('rvandroid.tools.registry.ToolRegistry') as mock_registry_cls:
                mock_tool_registry = Mock()
                mock_registry_cls.get_instance.return_value = mock_tool_registry

                mock_tools = [Mock(), Mock()]
                mock_tool_registry.get_tools.return_value = mock_tools

                # Mock ExperimentController
                with patch(
                        'rvandroid.experiment.workflow.experiment_controller.ExperimentController') as mock_controller_cls:
                    mock_controller = Mock()
                    mock_controller_cls.return_value = mock_controller

                    # Mock LoggingManager
                    with patch('rvandroid.experiment.workflow.experiment_controller.LoggingManager'):
                        # Import the execute function here to ensure all patches are active
                        from rvandroid.experiment.workflow.experiment_controller import execute

                        # Call the execute function
                        execute()

                        # Verify controller was created and execute was called
                        mock_controller_cls.assert_called_once()
                        mock_controller.execute.assert_called_once()

    def test_execute_with_provided_tools(self):
        """Test the execute function with explicitly provided tools."""
        # Mock the Configuration class and instance
        with patch('rvandroid.config.configuration.Configuration') as mock_config_cls:
            mock_config = Mock()
            mock_config_cls.get_instance.return_value = mock_config

            # Configure mock return values
            mock_config.get_int.return_value = 2
            mock_config.get_list.return_value = [60]
            mock_config.get_str.return_value = ""
            mock_config.get_bool.return_value = True

            # Create mock tools to provide explicitly
            provided_tools = [Mock(), Mock()]

            # Mock ExperimentController
            with patch(
                    'rvandroid.experiment.workflow.experiment_controller.ExperimentController') as mock_controller_cls:
                mock_controller = Mock()
                mock_controller_cls.return_value = mock_controller

                # Mock LoggingManager
                with patch('rvandroid.experiment.workflow.experiment_controller.LoggingManager'):
                    # Import the execute function here to ensure all patches are active
                    from rvandroid.experiment.workflow.experiment_controller import execute

                    # Call execute with explicit tools
                    execute(tools=provided_tools)

                    # Verify controller.execute was called with provided tools
                    mock_controller.execute.assert_called_once()

                    # Extract args from call
                    args, kwargs = mock_controller.execute.call_args

                    # Verify tools were passed correctly
                    assert kwargs['tools'] == provided_tools
