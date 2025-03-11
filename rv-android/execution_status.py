import json
import sys

from rvandroid import utils
from rvandroid.experiment import Memory
import os
from rvandroid.experiment.task import Task, DEFAULT_DATETIME
import rvandroid.parser.log.logcat_parser as parser
from rvandroid.constants import EXTENSION_LOGCAT

def status(memory_file: str) -> dict:
    results_dir = os.path.dirname(memory_file)
    print(f"results_dir={results_dir}")
    try:
        memory = Memory.read(memory_file)
    except Exception as e:
        return {"tasks": 0, "completed": 0, "pct": 0.0, "errors": [f"Error reading memory file: {e!s}"]}

    completed_tasks = sum(task.executed for task in memory.tasks)
    total_tasks = len(memory.tasks)
    errors = [f"task={task}, error={task.error}" for task in memory.tasks if task.error]

    pct = round((completed_tasks / total_tasks) * 100, 2) if total_tasks else 0.0

    apks = get_apks(memory)
    tasks = get_tasks(memory, results_dir)

    return {"total": total_tasks, "completed": completed_tasks, "pct": pct, "errors": errors, "tasks": tasks, "apks": apks}


def get_apks(memory: Memory):
    apks = {}
    for task in memory.tasks:
        if task.apk not in apks:
            apks[task.apk] = {
                "total_tasks": 0,
                "executed": 0,
                "pct": 0.0
            }

        executed = apks[task.apk]["executed"]
        if task.executed:
            executed = executed + 1
        total = apks[task.apk]["total_tasks"] + 1

        apks[task.apk] = {
            "total_tasks": total,
            "executed": executed,
            "pct": (executed*100)/total
        }
    return apks


def get_tasks(memory: Memory, results_dir: str):
    tasks = []
    for task in memory.tasks:
        time_tmp: float = 0.0
        if task.executed:
            time_tmp = (task.finish_time - task.start_time).total_seconds()
        start = ""
        if task.start_time != DEFAULT_DATETIME:
            start = utils.datetime_to_string(task.start_time)
        finish = ""
        if task.finish_time != DEFAULT_DATETIME:
            finish = utils.datetime_to_string(task.finish_time)
        tasks.append({
            "task": repr(task),
            "executed": task.executed,
            "start": start,
            "finish": finish,
            "time": time_tmp,
            "errors": get_errors(task, results_dir)
        })
    return tasks


def get_errors(task: Task, results_dir: str):
    errors = []
    if not task.executed:
        return errors
    base_name = "{0}__{1}__{2}__{3}".format(task.apk, task.repetition, task.timeout, task.tool)
    apk_results_dir = os.path.join(results_dir, task.apk)
    task.logcat_file = os.path.join(apk_results_dir, "{}{}".format(base_name, EXTENSION_LOGCAT))
    rvsec_errors, _, _ = parser.parse_logcat_file(task.logcat_file)
    for error in rvsec_errors:
        errors.append({
            "msg": error.unique_msg,
            "time_occurred": utils.datetime_to_string(error.time_occurred),
            "time_since_task_start": str(error.time_occurred - task.start_time)
        })
    return errors




if __name__ == '__main__':
    memory_file_path = sys.argv[1]
    # memory_file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20241119111618/execution_memory.json"
    if os.path.exists(memory_file_path):
        data = status(memory_file_path)
        print(json.dumps(data, indent=2))
