
import analysis.coverage as cov


def execute(results_dir: str):
    cov.execute(results_dir)


if __name__ == '__main__':
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste"
    execute(result_dir)
