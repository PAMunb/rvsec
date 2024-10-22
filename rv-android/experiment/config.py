
from tools.tool_spec import AbstractTool

repetitions: int = 0

timeouts: list[int] = []

tools: list[AbstractTool] = []

available_tools: list[AbstractTool] = []

generate_monitors = True
instrument = True
static_analysis = True
skip_experiment = False

no_window = True

memory_file = ""
