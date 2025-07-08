# Debug executor behavior
from unittest.mock import MagicMock
from rv_android_core.domain.task import Task, TaskConfiguration
from rv_platform.execution.executor import TaskExecutor
from rv_android_core.domain.app import App

# Create basic config
config = TaskConfiguration(
    apk_name="test.apk",
    repetition=1,
    timeout=60,
    tool_name="monkey"
)

# Create task with app
task = Task(config)
app = MagicMock(spec=App)
app.name = "test.apk"
task.set_app(app)

# Create mock tool
mock_tool = MagicMock()
mock_tool.name = "monkey"

# Create executor
executor = TaskExecutor(task, mock_tool)

# Add failing component
mock_component = MagicMock()
mock_component.execute.return_value = False
mock_component.name = "FailingComponent"

print(f"Component execute method: {mock_component.execute}")
print(f"Component execute return value: {mock_component.execute.return_value}")

executor.register_component(mock_component)

print(f"Number of components: {len(executor.components)}")
print(f"Component has execute: {hasattr(mock_component, 'execute')}")

# Try to execute
try:
    result = executor.execute()
    print(f"Execution result: {result}")
    print(f"Task state: {task.result.state}")
    print(f"Error message: {task.result.error_message}")
except Exception as e:
    print(f"Exception occurred: {e}")