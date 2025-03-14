# rvandroid/experiment/example_usage.py
"""
Example usage of the refactored task management system.
"""

# import logging
# import os
# from typing import List
#
# from rvandroid.app import App
# from rvandroid.experiment.event_system import EventBus, EventType, event_handler
# from rvandroid.experiment.execution_manager import ExecutionManager
# from rvandroid.experiment.task_storage import TaskStorage
# from rvandroid.tools.tool_spec import AbstractTool
#
#
# def setup_example():
#     """Set up and run an example experiment"""
#     # Configure logging
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger(__name__)
#
#     # Create task storage
#     results_dir = os.path.join(os.getcwd(), "results")
#     os.makedirs(results_dir, exist_ok=True)
#     storage_file = os.path.join(results_dir, "tasks.json")
#     storage = TaskStorage(storage_file)
#
#     # Create event bus
#     event_bus = EventBus.get_instance()
#
#     # Register event handlers
#     @event_handler(EventType.TASK_STARTED)
#     def handle_task_started(event):
#         logger.info(f"Task {event.task_id} started")
#
#     @event_handler(EventType.TASK_COMPLETED)
#     def handle_task_completed(event):
#         logger.info(f"Task {event.task_id} completed")
#
#     @event_handler(EventType.EXPERIMENT_STARTED)
#     def handle_experiment_started(event):
#         logger.info(f"Experiment {event.experiment_id} started: {event.message}")
#
#     # Create execution manager
#     manager = ExecutionManager(storage, event_bus)
#
#     # Mock apps and tools for the example
#     class MockApp(App):
#         def __init__(self, name):
#             self.name = name
#             self.package_name = f"com.example.{name}"
#             self.permissions = []
#
#     class MockTool(AbstractTool):
#         def __init__(self, name):
#             super().__init__(name, f"Mock tool: {name}", "")
#
#         def execute_tool_specific_logic(self, task, app):
#             logger.info(f"Executing {self.name} on {app.name}")
#             # Simulate tool execution
#             import time
#             time.sleep(1)
#
#         # Create mock apps and tools
#         apps: List[App] = [MockApp(f"app{i}") for i in range(2)]
#         tools: List[AbstractTool] = [MockTool(name) for name in ["monkey", "droidbot"]]
#
#         # Set up execution
#         manager.setup_execution(
#             apks=apps,
#             repetitions=2,
#             timeouts=[60, 120],
#             tools=tools,
#             no_window=True
#         )
#
#         # Run all tasks
#         logger.info("Starting experiment execution")
#         result = manager.run_all_tasks()
#
#         # Print statistics
#         stats = manager.get_statistics()
#         logger.info(f"Execution complete. Statistics: {stats}")
#
#         return result, manager
#
#     if __name__ == "__main__":
#         setup_example()