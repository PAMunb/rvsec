"""Lê scripts/campanha.env para os scripts Python da campanha.

O bash faz `source` do mesmo arquivo; aqui só se aceita o subconjunto que os dois leem igual:
`KEY=VALUE` ou `KEY="VALUE"`, comentários com `#` no início da linha.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP_DIR = HERE.parent
ROOT = HERE.parents[1]  # rv-android/
RESULTS = ROOT / "data" / "results"


def load(path: Path = HERE / "campanha.env") -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        env[key] = value.strip().strip('"')
    return env


#: CAMPANHA_ENV aponta outro arquivo, para ensaiar os scripts sobre uma campanha antiga.
ENV = load(Path(os.environ["CAMPANHA_ENV"])) if os.environ.get("CAMPANHA_ENV") else load()
NAME = ENV["NAME"]
SMOKE_NAME = ENV["SMOKE_NAME"]
CONTAINERS = int(ENV["CONTAINERS"])
SMOKE_CONTAINERS = int(ENV["SMOKE_CONTAINERS"])
TIMEOUTS = tuple(int(t) for t in ENV["TIMEOUTS"].split(","))
REPS = tuple(range(1, int(ENV["REPS"]) + 1))
SMOKE_TIMEOUT = int(ENV["SMOKE_TIMEOUT"])
SMOKE_APKS = ENV["SMOKE_APKS"].split(",")
FILTERS = ROOT / "data" / f"{NAME}_filters"

#: Os braços saem de TOOLS pela mesma expansão que o gen_compare usa para o total de tasks,
#: com o rótulo do consolidador (`variant='default'` colapsa no nome seco).
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "rv-experiment-compare" / "scripts"))
from gen_compare import arms_of  # noqa: E402

ARMS = arms_of(ENV["TOOLS"])


def containers(name: str = NAME, n: int = CONTAINERS) -> list:
    return [f"{name}_{i:02d}" for i in range(n)]
