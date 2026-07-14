#!/usr/bin/env python3
"""rv_status — status unificado de um experimento rv-android (substitui os monitor_*.sh).

Lê `tasks.json` de cada container e mostra progresso REAL de execução (não só
container up/down): global, por container, por tool, por timeout (pass), APKs
travados e breakdown de erros — com throughput e ETA.

Funciona ao vivo na VM (com `docker`) e offline sobre results copiados (sem docker).

Uso:
    # auto-descobre containers exp_* sob ./results, deriva expected de 169×11×3×3 passes
    python3 scripts/rv_status.py --apks 169 --tools 11 --reps 3 --timeouts 60,180,300

    # watch contínuo a cada 30s
    python3 scripts/rv_status.py --apks 169 --tools 11 --reps 3 --timeouts 60,180,300 --watch 30

    # snapshot estruturado (para coleta/automação)
    python3 scripts/rv_status.py --apks 169 --tools 11 --reps 3 --timeouts 60,180,300 --json

`tasks.json` indexa por task_id (UUID); um re-run (resume/mop-up) deixa várias
entradas para a MESMA identidade (apk, tool, variant, rep, timeout). O status
DEDUPLICA por identidade (estado efetivo COMPLETED > ativo > falha > pendente),
então ok/fail/total contam identidades distintas, não entradas brutas.

`expected` REAL: sem `--apks`, é derivado dos APKs DISTINTOS vistos nesta VM
× tools × reps × nº de timeouts (por-VM correto). Use `--apks 169` só para o
total do experimento inteiro, ou `--expected N` para forçar.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DONE_STATES = {"COMPLETED"}
FAIL_STATES = {"FAILED", "ERROR"}
# Estados "ativos" (tarefa em andamento, ainda não finalizada).
ACTIVE_STATES = {"INITIALIZING", "READY", "RUNNING", "INSTALLING", "EXECUTING"}

# Classificação de erro por regex sobre (error_message + state). Ordem importa.
ERROR_BUCKETS = [
    ("timeout", re.compile(r"time?out|timed out", re.I)),
    ("oom/killed", re.compile(r"\boom\b|out of memory|killed|exit ?137|sigkill|memory", re.I)),
    ("install/adb", re.compile(r"install|adb|INSTALL_FAILED|device offline", re.I)),
    ("emulator/boot", re.compile(r"emulator|boot|avd|kvm|snapshot", re.I)),
    ("crash/verify", re.compile(r"verifyerror|exception|crash|traceback|nullpointer", re.I)),
]


def reconstruct_tool(tool_config: dict) -> str:
    """name[:variant] — variante omitida quando 'default'."""
    name = tool_config.get("name", "?")
    variant = tool_config.get("variant")
    if variant and variant != "default":
        return f"{name}:{variant}"
    return name


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except (ValueError, TypeError):
        return None


def classify_error(state: str, message) -> str:
    text = f"{state} {message or ''}"
    for label, rx in ERROR_BUCKETS:
        if rx.search(text):
            return label
    if state in FAIL_STATES:
        return "other-fail"
    return "unknown"


def docker_status(container: str) -> str:
    if not shutil.which("docker"):
        return "-"
    try:
        out = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else "gone"
    except (subprocess.SubprocessError, OSError):
        return "-"


def load_container_apks(env_file: str, filters_dir: str, prefix: str) -> dict:
    """Mapeia container -> conjunto AUTORITATIVO de APKs, a partir do `.env.mN`.

    `.env.mN` define `BATCH_<i>=batch_<nn>` e o compose liga o serviço `{prefix}{i:02d}`
    ao `BATCH_<i>`. Para cada um, lê `<filters_dir>/<batch>.txt` (1 nome de APK por
    linha) = a lista de APKs que aquele container DEVIA rodar. É a fonte da verdade do
    expected (não enxergável nos dados quando um APK tem 0 task — ex.: container morto
    por OOM antes de chegar nele).
    """
    mapping = {}
    try:
        with open(env_file) as fh:
            env_lines = fh.readlines()
    except OSError:
        return mapping
    for line in env_lines:
        m = re.match(r"\s*BATCH_(\d+)\s*=\s*(\S+)", line)
        if not m:
            continue
        idx, batch = int(m.group(1)), m.group(2).strip().strip('"\'')
        container = f"{prefix}{idx:02d}"
        batch_file = Path(filters_dir) / f"{batch}.txt"
        try:
            with open(batch_file) as bf:
                mapping[container] = {ln.strip() for ln in bf if ln.strip()}
        except OSError:
            mapping[container] = set()
    return mapping


def discover_containers(results_dir: Path, prefix: str, explicit) -> list:
    if explicit:
        return list(explicit)
    found = []
    for path in sorted(glob.glob(str(results_dir / f"{prefix}*"))):
        p = Path(path)
        if p.is_dir() and (p / p.name / "tasks.json").exists():
            found.append(p.name)
    return found


def task_identity(task: dict) -> tuple:
    """Identidade lógica de uma task: (apk, tool, variant, rep, timeout).

    Igual à chave usada pelo resume do rv-platform. Duas entradas com a mesma
    identidade são a MESMA unidade de trabalho, mesmo com task_id (UUID) distinto.
    """
    cfg = task.get("config", {})
    tc = cfg.get("tool_config", {})
    return (cfg.get("apk_name"), tc.get("name"), tc.get("variant"),
            cfg.get("repetition"), cfg.get("timeout"))


def effective_entry(group: list) -> tuple:
    """Colapsa as entradas de uma identidade num único (task, state) efetivo.

    Prioridade COMPLETED > ativo > falha > pendente: sucesso e execução-em-curso
    vencem entradas antigas. Sem isso, uma identidade ERROR→COMPLETED (re-run)
    seria contada como ok E fail ao mesmo tempo (total inflado, fail que nunca cai).
    """
    def pick(states):
        return [t for t in group if (t.get("result") or {}).get("state") in states]
    for bucket in (DONE_STATES, ACTIVE_STATES, FAIL_STATES):
        hit = pick(bucket)
        if hit:
            return hit[-1], (hit[-1].get("result") or {}).get("state")
    return group[-1], (group[-1].get("result") or {}).get("state", "UNKNOWN")


def load_container(results_dir: Path, container: str) -> dict:
    """Lê tasks.json de 1 container, DEDUPLICA por identidade e agrega.

    tasks.json indexa por task_id (UUID novo a cada execução), então uma task
    re-executada (resume/mop-up) deixa MAIS DE UMA entrada para a mesma
    identidade. Contar entradas brutas inflaria ok/fail. Aqui cada identidade é
    colapsada num único estado efetivo e contada UMA vez. `duplicates` registra
    quantas entradas extras foram absorvidas.
    """
    tasks_file = results_dir / container / container / "tasks.json"
    info = {
        "container": container,
        "docker": docker_status(container),
        "completed": 0, "failed": 0, "active": 0, "pending": 0, "total": 0,
        "duplicates": 0,
        "by_tool": defaultdict(lambda: Counter()),
        "by_timeout": defaultdict(lambda: Counter()),
        "by_rep": defaultdict(lambda: Counter()),
        "errors": Counter(),
        "apk_states": defaultdict(list),       # apk -> [states] (1 por identidade)
        "running_now": [],                     # (apk, tool, age_s)
        "first_start": None, "last_end": None,
        "last_activity": None,
        "exists": tasks_file.exists(),
        "expected_tasks": None,                # preenchido se houver lista autoritativa
        "expected_apks": None,                 # nº de APKs que o container DEVIA rodar
        "missing_apks": [],                    # APKs autoritativos com 0 task
    }
    if not tasks_file.exists():
        return info
    try:
        with open(tasks_file) as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        info["exists"] = False
        return info

    info["last_activity"] = os.path.getmtime(tasks_file)
    now = time.time()

    # tasks pode ser lista ou dict {id: task}; topo pode ser {"tasks": ...} ou a coleção.
    raw = data.get("tasks", data) if isinstance(data, dict) else data
    entries = list(raw.values()) if isinstance(raw, dict) else raw

    # agrupa por identidade lógica (colapsa duplicatas de re-run)
    by_ident = defaultdict(list)
    for task in entries:
        by_ident[task_identity(task)].append(task)

    for group in by_ident.values():
        info["duplicates"] += len(group) - 1
        task, state = effective_entry(group)
        cfg = task.get("config", {})
        res = task.get("result", {})
        tool = reconstruct_tool(cfg.get("tool_config", {}))
        timeout = cfg.get("timeout", "?")
        rep = cfg.get("repetition", "?")
        apk = cfg.get("apk_name", "?")

        info["total"] += 1
        info["by_tool"][tool][state] += 1
        info["by_timeout"][timeout][state] += 1
        info["by_rep"][rep][state] += 1
        info["apk_states"][apk].append(state)

        if state in DONE_STATES:
            info["completed"] += 1
        elif state in FAIL_STATES:
            info["failed"] += 1
            info["errors"][classify_error(state, res.get("error_message"))] += 1
        elif state in ACTIVE_STATES:
            info["active"] += 1
            st = parse_ts(res.get("start_time")) or parse_ts(res.get("tool_execution_start"))
            age = int(now - st) if st else None
            info["running_now"].append((apk, tool, age))
        else:
            info["pending"] += 1

        # timestamps: varre todas as entradas da identidade (não só a efetiva)
        for t in group:
            r = t.get("result", {})
            st = parse_ts(r.get("start_time"))
            et = parse_ts(r.get("end_time"))
            if st and (info["first_start"] is None or st < info["first_start"]):
                info["first_start"] = st
            if et and (info["last_end"] is None or et > info["last_end"]):
                info["last_end"] = et
    return info


def aggregate(containers_info: list) -> dict:
    agg = {
        "completed": 0, "failed": 0, "active": 0, "pending": 0, "total": 0,
        "duplicates": 0,
        "by_tool": defaultdict(lambda: Counter()),
        "by_timeout": defaultdict(lambda: Counter()),
        "errors": Counter(),
        "first_start": None, "last_end": None,
        "stuck_failing": [],   # apks com 0 COMPLETED e ≥1 finalizado
        "running_now": [],
    }
    apk_states_global = defaultdict(list)
    for ci in containers_info:
        for k in ("completed", "failed", "active", "pending", "total", "duplicates"):
            agg[k] += ci[k]
        for tool, ctr in ci["by_tool"].items():
            agg["by_tool"][tool].update(ctr)
        for to, ctr in ci["by_timeout"].items():
            agg["by_timeout"][to].update(ctr)
        agg["errors"].update(ci["errors"])
        for apk, states in ci["apk_states"].items():
            apk_states_global[apk].extend(states)
        agg["running_now"].extend(
            (ci["container"], apk, tool, age) for (apk, tool, age) in ci["running_now"]
        )
        for key in ("first_start", "last_end"):
            v = ci[key]
            if v and (agg[key] is None or (v < agg[key] if key == "first_start" else v > agg[key])):
                agg[key] = v

    for apk, states in apk_states_global.items():
        finished = [s for s in states if s in DONE_STATES | FAIL_STATES]
        if finished and not any(s in DONE_STATES for s in finished):
            agg["stuck_failing"].append((apk, len(finished)))
    agg["stuck_failing"].sort(key=lambda x: -x[1])
    agg["apk_set"] = set(apk_states_global.keys())   # APKs com ≥1 task vista
    agg["apks"] = len(agg["apk_set"])
    return agg


def fmt_hours(seconds) -> str:
    if seconds is None or seconds < 0:
        return "?"
    h = seconds / 3600
    return f"{h:.1f}h" if h >= 1 else f"{seconds/60:.0f}m"


def build_snapshot(args) -> dict:
    results_dir = Path(args.results)
    containers = discover_containers(results_dir, args.prefix, args.containers)
    infos = [load_container(results_dir, c) for c in containers]
    agg = aggregate(infos)

    passes = len(args.timeouts) if args.timeouts else 1

    # Lista AUTORITATIVA de APKs POR CONTAINER (fonte da verdade do expected):
    # lida do .env.mN (BATCH_i -> {prefix}{i:02d}) + arquivos de filtro. É a única
    # forma de enxergar APK com 0 task (invisível nos dados — ex.: container morto
    # por OOM antes de chegar nele). Sem --env, cai no floor (APKs distintos vistos).
    container_apks = load_container_apks(args.env, args.filters_dir, args.prefix) if args.env else {}
    global_missing = []   # (container, apk) autoritativo com 0 task
    if container_apks:
        for ci in infos:
            auth = container_apks.get(ci["container"])
            if auth is None:
                continue
            seen = set(ci["apk_states"].keys())
            ci["expected_apks"] = len(auth)
            ci["missing_apks"] = sorted(auth - seen)
            if args.tools and args.reps:
                ci["expected_tasks"] = len(auth) * args.tools * args.reps * passes
            global_missing.extend((ci["container"], a) for a in ci["missing_apks"])

    if container_apks:
        n_apks = sum(len(v) for k, v in container_apks.items()
                     if k in {ci["container"] for ci in infos})
    elif args.apks:
        n_apks = args.apks            # força total do experimento inteiro
    else:
        n_apks = agg["apks"]          # floor: distintos vistos (subestima se há APK 0-task)
    per_timeout = (n_apks * args.tools * args.reps) if (args.tools and args.reps) else None

    if args.expected:
        expected = args.expected
    elif container_apks and args.tools and args.reps:
        expected = sum(ci.get("expected_tasks") or 0 for ci in infos)
    elif per_timeout:
        expected = per_timeout * passes
    else:
        expected = agg["total"]

    done = agg["completed"] + agg["failed"]
    remaining = max(0, expected - done)

    # throughput + ETA: taxa agregada sobre o span real (offline-safe).
    span = None
    if agg["first_start"]:
        end_ref = max(filter(None, [agg["last_end"], time.time() if any(i["docker"] == "running" for i in infos) else None]), default=agg["last_end"])
        if end_ref:
            span = end_ref - agg["first_start"]
    rate_per_h = (done / (span / 3600)) if span and span > 0 and done else None
    eta_seconds = (remaining / rate_per_h * 3600) if rate_per_h else None

    return {
        "results_dir": str(results_dir),
        "containers": infos,
        "agg": agg,
        "expected": expected,
        "n_apks": n_apks,
        "per_timeout_expected": per_timeout,
        "global_missing": global_missing,
        "done": done,
        "remaining": remaining,
        "pct": (100 * done / expected) if expected else 0,
        "span_seconds": span,
        "rate_per_h": rate_per_h,
        "eta_seconds": eta_seconds,
    }


def render(snap: dict, args) -> str:
    agg = snap["agg"]
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"=== rv-status @ {ts}  ({snap['results_dir']}) ===")

    # --- header global ---
    pct = snap["pct"]
    bar_w = 30
    fill = int(bar_w * pct / 100)
    bar = "#" * fill + "-" * (bar_w - fill)
    basis = ""
    if snap.get("per_timeout_expected"):
        passes = len(args.timeouts) if args.timeouts else 1
        basis = f" (apks={snap['n_apks']}×tools×reps×{passes}p)"
    lines.append(
        f"[{bar}] {pct:5.1f}%   "
        f"done={snap['done']}  (ok={agg['completed']} fail={agg['failed']})  "
        f"active={agg['active']}  remaining={snap['remaining']}  expected={snap['expected']}{basis}"
    )
    if agg.get("duplicates"):
        lines.append(
            f"  (dedup por identidade: {agg['duplicates']} entradas duplicadas de "
            f"re-run absorvidas — ok/fail/total contam identidades distintas)"
        )
    rate = snap["rate_per_h"]
    extras = [f"elapsed={fmt_hours(snap['span_seconds'])}"]
    if rate:
        extras.append(f"throughput={rate:.0f} tasks/h")
        extras.append(f"ETA~{fmt_hours(snap['eta_seconds'])}")
        if snap["eta_seconds"]:
            finish = datetime.fromtimestamp(time.time() + snap["eta_seconds"]).strftime("%m-%d %H:%M")
            extras.append(f"finish~{finish}")
    lines.append("  " + "   ".join(extras))

    # --- por container ---
    lines.append("")
    lines.append(f"{'CONTAINER':<14}{'DOCKER':<10}{'OK':>6}{'FAIL':>6}{'ACT':>5}{'TOTAL':>7}{'EXPECT':>7}{'%':>6}  {'RUNNING (apk/tool, age)':<34} {'LAST':>6}")
    lines.append("-" * 110)
    for ci in snap["containers"]:
        done_c = ci["completed"] + ci["failed"]
        # % contra o expected REAL do container (se houver lista autoritativa), senão sobre o visto
        denom = ci.get("expected_tasks") or ci["total"]
        exp_c = ci.get("expected_tasks") or ci["total"]
        pct_c = (100 * done_c / denom) if denom else 0
        run = "-"
        if ci["running_now"]:
            apk, tool, age = ci["running_now"][0]
            age_s = f"{age//60}m" if age else "?"
            run = f"{apk[:22]} / {tool} ({age_s})"
        last = "-"
        if ci["last_activity"]:
            mins = int((time.time() - ci["last_activity"]) / 60)
            last = f"{mins}m"
        lines.append(
            f"{ci['container']:<14}{ci['docker']:<10}{ci['completed']:>6}{ci['failed']:>6}"
            f"{ci['active']:>5}{ci['total']:>7}{exp_c:>7}{pct_c:>5.0f}%  {run:<34} {last:>6}"
        )

    # --- por tool ---
    lines.append("")
    lines.append(f"{'TOOL':<26}{'OK':>7}{'FAIL':>7}{'ACT':>6}{'TOTAL':>7}")
    lines.append("-" * 53)
    for tool in sorted(agg["by_tool"]):
        ctr = agg["by_tool"][tool]
        ok = sum(ctr[s] for s in DONE_STATES)
        fail = sum(ctr[s] for s in FAIL_STATES)
        act = sum(ctr[s] for s in ACTIVE_STATES)
        lines.append(f"{tool:<26}{ok:>7}{fail:>7}{act:>6}{sum(ctr.values()):>7}")

    # --- por timeout (pass) ---
    if len(agg["by_timeout"]) > 1:
        exp_to = snap.get("per_timeout_expected")
        lines.append("")
        hdr = f"{'TIMEOUT(pass)':<16}{'OK':>7}{'FAIL':>7}{'ACT':>6}{'TOTAL':>7}"
        if exp_to:
            hdr += f"{'EXPECT':>8}{'FALTAM':>8}"
        lines.append(hdr)
        lines.append("-" * (43 + (16 if exp_to else 0)))
        for to in sorted(agg["by_timeout"], key=lambda x: (x == "?", x)):
            ctr = agg["by_timeout"][to]
            ok = sum(ctr[s] for s in DONE_STATES)
            fail = sum(ctr[s] for s in FAIL_STATES)
            act = sum(ctr[s] for s in ACTIVE_STATES)
            row = f"{str(to)+'s':<16}{ok:>7}{fail:>7}{act:>6}{sum(ctr.values()):>7}"
            if exp_to:
                row += f"{exp_to:>8}{max(0, exp_to - ok):>8}"
            lines.append(row)

    # --- APKs com 0 task (autoritativo - visto): só com --env ---
    gm = snap.get("global_missing") or []
    if gm:
        lines.append("")
        lines.append(f"APKs com 0 TASK ({len(gm)}) — no filtro mas nunca executados (esperam mop-up):")
        for c, apk in sorted(gm):
            lines.append(f"  [{c}] {apk}")

    # --- breakdown de erros ---
    if agg["errors"]:
        lines.append("")
        lines.append("ERROS (top):")
        for label, n in agg["errors"].most_common(args.top_errors):
            lines.append(f"  {label:<16}{n:>6}")

    # --- APKs travados (0 sucesso, ≥1 finalizado) ---
    if agg["stuck_failing"]:
        lines.append("")
        lines.append(f"APKs SÓ-FALHA ({len(agg['stuck_failing'])}) — candidatos a investigar/drop:")
        for apk, n in agg["stuck_failing"][:args.top_errors]:
            lines.append(f"  {apk:<48} {n} task(s) finalizada(s), 0 ok")

    # --- tarefas rodando há muito tempo ---
    long_running = [r for r in agg["running_now"] if r[3] and r[3] > args.stuck_min * 60]
    if long_running:
        lines.append("")
        lines.append(f"RODANDO > {args.stuck_min}min:")
        for c, apk, tool, age in sorted(long_running, key=lambda x: -(x[3] or 0))[:args.top_errors]:
            lines.append(f"  [{c}] {apk[:40]} / {tool}  {age//60}m")

    return "\n".join(lines)


def _ok_err_done(counter: Counter) -> dict:
    """Reduz um Counter de estados a {ok, err, done} (done = ok + err).

    Usado no export por-container de by_timeout/by_rep para o consumidor (health_check)
    não precisar reclassificar estados — os conjuntos DONE/FAIL vivem só aqui.
    """
    ok = sum(counter[s] for s in DONE_STATES)
    err = sum(counter[s] for s in FAIL_STATES)
    return {"ok": ok, "err": err, "done": ok + err}


def to_json(snap: dict) -> dict:
    """Versão serializável (sem defaultdict/Counter aninhados pesados)."""
    agg = snap["agg"]
    return {
        "expected": snap["expected"], "done": snap["done"],
        "n_apks": snap.get("n_apks"), "per_timeout_expected": snap.get("per_timeout_expected"),
        "duplicates": agg.get("duplicates", 0),
        "completed": agg["completed"], "failed": agg["failed"],
        "active": agg["active"], "remaining": snap["remaining"],
        "pct": round(snap["pct"], 2),
        "throughput_per_h": round(snap["rate_per_h"], 1) if snap["rate_per_h"] else None,
        "eta_seconds": int(snap["eta_seconds"]) if snap["eta_seconds"] else None,
        "by_tool": {t: dict(c) for t, c in agg["by_tool"].items()},
        "by_timeout": {str(t): dict(c) for t, c in agg["by_timeout"].items()},
        "errors": dict(agg["errors"]),
        "stuck_failing": [a for a, _ in agg["stuck_failing"]],
        "zero_task_apks": [{"container": c, "apk": a} for c, a in (snap.get("global_missing") or [])],
        "containers": [
            {"container": ci["container"], "docker": ci["docker"],
             "completed": ci["completed"], "failed": ci["failed"],
             "active": ci["active"], "total": ci["total"],
             "expected_tasks": ci.get("expected_tasks"),
             "by_timeout": {str(t): _ok_err_done(c) for t, c in ci["by_timeout"].items()},
             "by_rep": {str(r): _ok_err_done(c) for r, c in ci["by_rep"].items()}}
            for ci in snap["containers"]
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="Status unificado de experimento rv-android")
    ap.add_argument("--results", default="results", help="dir base dos results (default: results)")
    ap.add_argument("--prefix", default="exp_", help="prefixo dos containers (default: exp_)")
    ap.add_argument("--containers", type=lambda s: s.split(","), help="lista explícita c1,c2,...")
    ap.add_argument("--apks", type=int, help="nº de APKs (para derivar expected)")
    ap.add_argument("--tools", type=int, help="nº de tools")
    ap.add_argument("--reps", type=int, help="repetições")
    ap.add_argument("--timeouts", type=lambda s: [x for x in s.split(",") if x],
                    default=["60", "180", "300"], help="passes de timeout (default: 60,180,300)")
    ap.add_argument("--expected", type=int, help="override do total esperado")
    ap.add_argument("--env", help=".env.mN p/ ler a lista AUTORITATIVA de APKs por container "
                                  "(BATCH_i->container) e detectar APKs com 0 task")
    ap.add_argument("--filters-dir", default="filters", help="dir dos batch_*.txt (default: filters)")
    ap.add_argument("--watch", type=int, metavar="SEC", help="loop a cada SEC segundos")
    ap.add_argument("--json", action="store_true", help="emite snapshot JSON e sai")
    ap.add_argument("--stuck-min", type=int, default=20, help="limiar (min) p/ flag de tarefa longa")
    ap.add_argument("--top-errors", type=int, default=8, help="quantos itens listar nas seções top")
    args = ap.parse_args()

    if args.json:
        print(json.dumps(to_json(build_snapshot(args)), indent=2))
        return

    if args.watch:
        try:
            while True:
                snap = build_snapshot(args)
                # ANSI clear (sem shell) — limpa tela + move cursor ao topo.
                sys.stdout.write("\033[2J\033[H")
                print(render(snap, args))
                time.sleep(args.watch)
        except KeyboardInterrupt:
            sys.exit(0)
    else:
        print(render(build_snapshot(args), args))


if __name__ == "__main__":
    main()
