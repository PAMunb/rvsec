import argparse
import importlib
import logging
import os
import sys
import time

import experiment_01
import utils

available_tools = {}
output_formats = {}


def qualified_name(p):
    return p.replace(".py", "").replace("./", "").replace("/", ".")


def load_tools():
    """Load all available tools.

     A tool must be defined in a subdirectory within
     the tools folder, in a python module named tool.py.
     This module must also declare a class named ToolSpec,
     which should inherit from AbstractTool.
    """
    for subdir, dirs, files in os.walk('.' + os.sep + 'tools'):
        for filename in files:
            if filename == 'tool.py':
                tool_module = importlib.import_module(qualified_name(subdir + os.sep + filename))
                tool_class = getattr(tool_module, 'ToolSpec')
                tool_instance = tool_class()
                available_tools[tool_instance.name] = tool_instance


def check_positive(value: int):
    if value <= 0:
        print("The value must be greater than zero: {}".format(value))
        exit(1)


program_description = f'''
Executes the 'Experiment 01' ... 

Examples:    
$ python main.py --no_window -tools monkey droidbot -r 3 -t 120 300 600 900
$ python main.py --list-tools

'''

if __name__ == '__main__':

    load_tools()

    # Start catching arguments
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)

    # list available tools
    parser.add_argument("--list-tools", help="list available tools", action="store_true")

    # List of test tools to be used in the experiment
    parser.add_argument('-tools', nargs='+', default=['monkey'],
                        help="List of test tools to be used in the experiment. EX: -tools monkey droidbot")

    # List of the execution timeouts in the experiment
    parser.add_argument('-t', nargs='+', default=[60],
                        help='List of the execution timeouts (in seconds) in the experiment. EX: -t 120 300', type=int)

    # Number of repetitions used in the experiment
    parser.add_argument('-r', default=1, help='Number of repetitions used in the experiment. EX: -r 10',
                        type=int)

    parser.add_argument("--no_window", help="Starts emulator with '-no-window'", action="store_true")

    # Enable DEBUG mode.
    parser.add_argument('--debug', help='Run in DEBUG mode (default: false)', dest='debug', action='store_true')

    parser.add_argument("--skip_monitors", help="Skip monitors generation", action="store_true")
    parser.add_argument("--skip_instrument", help="Skip instrumentation", action="store_true")
    # parser.add_argument("--skip_experiment", help="Skip experiment execution", action="store_true")

    args = parser.parse_args()
    # End catching arguments

    # TODO configurar log "direito"
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if args.debug else logging.INFO)

    # Validate arguments
    check_positive(args.r)
    for i in args.t:
        check_positive(i)
    tools = []
    for t in available_tools:
        for tool in args.tools:
            if t == tool:
                tools.append(available_tools[t])
    if len(tools) == 0:
        print("No valid tools selected.")
        exit(1)

    if args.list_tools:
        logging.info(" [Listing available tools] \n")
        for key in available_tools:
            print(" [{0}] {1} \n".format(key, available_tools[key].description))
        sys.exit(0)

    generate_monitors = not args.skip_monitors
    instrument = not args.skip_instrument

    logging.info('############# STARTING EXPERIMENT #############')
    start = time.time()

    experiment_01.execute(args.r, args.t, tools, generate_monitors, instrument, args.no_window)

    end = time.time()
    elapsed = end - start
    logging.info('It took {0} to complete'.format(utils.to_readable_time(elapsed)))

    logging.info('############# ENDING EXPERIMENT #############')
