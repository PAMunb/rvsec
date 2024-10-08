
from tools.tool_spec import AbstractTool


repetitions: int
repetitions = 0

timeouts: list[int]
timeouts = []

tools: list[AbstractTool]
tools = []

available_tools: list[AbstractTool]
available_tools = []

generate_monitors = True

instrument = True

skip_experiment = False

no_window = True

memory_file = ""
