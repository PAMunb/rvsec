
import pytest
from unittest.mock import MagicMock, patch
from rv_android_core.util.android.repository_initializer import initialize_repository_from_static_data
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.classes import Clazz as ClassDetails, Method as MethodDetails, Classes as ClassDetailsContainer
from rv_android_core.domain.coverage import LogcatRepository, ClassCoverageData, MethodCoverageData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph

@pytest.fixture
def mock_static_data():
    method1 = MethodDetails(
        class_name="com.example.MyClass",
        name="myMethod",
        signature="void myMethod()",
        params=[],
        reachable=True,
        reaches_mop=True,
        directly_reaches_mop=False
    )
    class1 = ClassDetails(
        name="com.example.MyClass",
        component_type="activity",
        methods=[method1]
    )
    class_container = ClassDetailsContainer()
    class_container.classes = {"com.example.MyClass": class1}
    
    return StaticAnalysisData(
        classes=class_container,
        windows=Windows(),
        wtg=WindowTransitionGraph()
    )

@pytest.fixture
def mock_repository():
    return MagicMock(spec=LogcatRepository)

def test_initialize_repository(mock_repository, mock_static_data):
    initialize_repository_from_static_data(mock_repository, mock_static_data)

    # Assert that add_class was called once
    mock_repository.add_class.assert_called_once()
    
    # Get the ClassCoverageData object that was passed to add_class
    call_args = mock_repository.add_class.call_args[0]
    class_coverage_data = call_args[0]

    assert isinstance(class_coverage_data, ClassCoverageData)
    assert class_coverage_data.name == "com.example.MyClass"
    assert class_coverage_data.component_type == "activity"

    # Assert that a method was added
    assert len(class_coverage_data.methods) == 1
    method_coverage_data = list(class_coverage_data.methods.values())[0]

    assert isinstance(method_coverage_data, MethodCoverageData)
    assert method_coverage_data.class_name == "com.example.MyClass"
    assert method_coverage_data.method_name == "myMethod"
    assert method_coverage_data.from_static_analysis is True

@patch('rv_android_core.util.android.repository_initializer.LoggingManager')
def test_logging_is_called(mock_logging_manager, mock_repository, mock_static_data):
    mock_logger = MagicMock()
    mock_logging_manager.get_instance.return_value.get_logger.return_value = mock_logger

    initialize_repository_from_static_data(mock_repository, mock_static_data)

    mock_logger.debug.assert_any_call("Initializing repository with 1 classes")
    mock_logger.debug.assert_any_call("Repository initialized successfully")
