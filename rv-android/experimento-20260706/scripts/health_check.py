#!/usr/bin/env python3
"""health_check.py — um ciclo de monitoramento das 4 VMs exp02 do experimento-20260706.

Roda de hora em hora (cron local). Para cada VM (m1..m4):
  - lê o progresso REAL (rv_status.py --json na VM, com expected POR VM via --env);
  - AUTO-RESUME: se o run JÁ foi iniciado (existe run.log) mas o
    run_experiment.sh não está mais vivo E a VM ainda não atingiu o alvo,
    relança o run (resume é idempotente via tasks.json). NUNCA faz o disparo
    inicial — só *retoma* um run que já foi iniciado manualmente;
  - registra uma seção com data/hora (status + problemas) em MONITORAMENTO.md.

Decisão de estado por VM (chaveada em `remaining` de contagem viva, não no
marcador de conclusão do run.log, que pode estar velho após um resume):
  - SSH falhou / sem dir do experimento  -> PROBLEMA (loga, sem ação)
  - run_experiment.sh vivo               -> RUNNING (sem ação)
  - run.log ausente                      -> NAO_INICIADO (sem ação — launch é manual)
  - remaining == 0                       -> CONCLUIDO (sem ação)
  - caso contrário (run morto, faltam)   -> RESUME (relança, com teto de segurança)

Teto de segurança: no máximo MAX_RESUMES resumes por VM (evita loop se um lote
falha de forma determinística). Ao estourar o teto, apenas registra em alto e
alto e não relança mais aquela VM.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

GCLOUD = "/snap/bin/gcloud"
ZONE = "us-central1-f"
REMOTE_EXP = "/home/pedro/experimento-20260706"
LOCAL_DIR = Path(__file__).resolve().parent.parent
LOG = LOCAL_DIR / "MONITORAMENTO.md"
STATE = LOCAL_DIR / ".monitor_state.json"
VMS = ["m1", "m2", "m3", "m4"]
TARGET = {"m1": 5544, "m2": 5544, "m3": 5445, "m4": 5148}
SSH_TIMEOUT = 150
MAX_RESUMES = 12  # teto de resumes por VM antes de exigir intervenção humana


def ssh(host, command, timeout=SSH_TIMEOUT):
    try:
        r = subprocess.run(
            [GCLOUD, "compute", "ssh", host, "--zone", ZONE, "--command", command],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "ssh timeout"
    except Exception as exc:  # noqa: BLE001 — cron: qualquer erro vira PROBLEMA logado
        return 1, "", str(exc)


def probe_cmd(vm):
    """Comando remoto: emite marcadores 'MARK ...' + o JSON do rv_status."""
    return (
        f"cd {REMOTE_EXP} 2>/dev/null || {{ echo 'MARK NO_EXP_DIR'; exit 0; }}\n"
        "pgrep -f run_experiment.sh >/dev/null && echo 'MARK RUN alive' "
        "|| echo 'MARK RUN dead'\n"
        "if [ -f run.log ]; then echo 'MARK LOG yes'; "
        "grep -q 'experimento concluído' run.log && echo 'MARK DONE_MARK yes' "
        "|| echo 'MARK DONE_MARK no'; else echo 'MARK LOG no'; fi\n"
        "echo 'MARK JSON_BEGIN'\n"
        f"python3 scripts/rv_status.py --json --env .env.{vm} "
        "--tools 11 --reps 3 --timeouts 60,180,300 2>/dev/null || echo '{{}}'\n"
    )


def parse_probe(stdout):
    """Separa os marcadores do bloco JSON."""
    marks = {}
    json_lines = []
    in_json = False
    for line in stdout.splitlines():
        if in_json:
            json_lines.append(line)
            continue
        if line.strip() == "MARK JSON_BEGIN":
            in_json = True
            continue
        if line.startswith("MARK "):
            parts = line.split(None, 2)
            if len(parts) == 2:
                marks[parts[1]] = True
            elif len(parts) == 3:
                marks[parts[1]] = parts[2]
    data = {}
    if json_lines:
        try:
            data = json.loads("\n".join(json_lines))
        except json.JSONDecodeError:
            data = {}
    return marks, data


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state):
    try:
        STATE.write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def resume(vm, host):
    """Relança run_experiment.sh na VM (append em run.log para preservar histórico)."""
    banner = datetime.now().strftime("=== RESUME %Y-%m-%d %H:%M:%S (local) ===")
    cmd = (
        f"cd {REMOTE_EXP} && echo '{banner}' >> run.log && "
        f"nohup ./scripts/run_experiment.sh {vm} >> run.log 2>&1 & "
        "echo resumed pid $!"
    )
    rc, out, err = ssh(host, cmd, timeout=60)
    return rc == 0, (out.strip() or err.strip())


def analyze(vm):
    """Coleta + decisão de UMA VM. Retorna dict com estado, métricas e problemas."""
    host = f"{vm}-exp02"
    rc, out, err = ssh(host, probe_cmd(vm))
    result = {"vm": vm, "problems": [], "action": "—"}

    if rc != 0:
        result["state"] = "SSH_FALHOU"
        detail = (err or out or f"rc={rc}").strip().splitlines()
        result["problems"].append(f"{vm}: SSH inacessível — {detail[-1] if detail else rc} (sem ação)")
        return result

    marks, data = parse_probe(out)
    if marks.get("NO_EXP_DIR"):
        result["state"] = "SEM_DIR"
        result["problems"].append(f"{vm}: dir do experimento ausente na VM (sem ação)")
        return result

    done = data.get("done", 0)
    completed = data.get("completed", 0)
    failed = data.get("failed", 0)
    active = data.get("active", 0)
    remaining = data.get("remaining", None)
    expected = data.get("expected", TARGET.get(vm))
    pct = data.get("pct", 0.0)
    eta = data.get("eta_seconds")
    result.update(
        done=done, completed=completed, failed=failed, active=active,
        remaining=remaining, expected=expected, pct=pct, eta=eta,
    )

    # coleta de problemas (sempre logados, independem da ação)
    errors = data.get("errors") or {}
    if errors:
        top = ", ".join(f"{k}:{v}" for k, v in sorted(errors.items(), key=lambda x: -x[1])[:6])
        result["problems"].append(f"{vm}: erros → {top}")
    stuck = data.get("stuck_failing") or []
    if stuck:
        result["problems"].append(f"{vm}: {len(stuck)} APK(s) só-falha → {', '.join(stuck[:5])}")
    zero = data.get("zero_task_apks") or []
    if zero:
        result["problems"].append(f"{vm}: {len(zero)} APK(s) com 0 task (esperam mop-up)")
    for c in data.get("containers") or []:
        if c.get("docker") in ("exited", "gone", "dead"):
            result["problems"].append(
                f"{vm}: container {c['container']} docker={c['docker']} "
                f"(ok={c.get('completed')} fail={c.get('failed')})"
            )

    run_alive = marks.get("RUN") == "alive"
    log_present = marks.get("LOG") == "yes"

    # decisão de estado + ação
    if run_alive:
        result["state"] = "RUNNING"
    elif not log_present:
        result["state"] = "NAO_INICIADO"
        result["problems"].append(f"{vm}: run.log ausente — run nunca iniciado (launch é manual, sem ação)")
    elif remaining is not None and remaining <= 0:
        result["state"] = "CONCLUIDO"
    else:
        result["state"] = "MORTO"  # iniciado, processo morto, ainda falta → resume
    return result


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = load_state()
    reports = [analyze(vm) for vm in VMS]

    # aplica RESUME onde o estado é MORTO, respeitando o teto
    for r in reports:
        if r.get("state") != "MORTO":
            continue
        vm = r["vm"]
        count = int(state.get(vm, 0))
        if count >= MAX_RESUMES:
            r["action"] = "TETO-RESUME"
            r["problems"].append(
                f"{vm}: !!! run morto e faltam {r.get('remaining')} tasks, mas teto de "
                f"{MAX_RESUMES} resumes atingido — INTERVENÇÃO HUMANA necessária (sem resume)"
            )
            continue
        ok, detail = resume(vm, f"{vm}-exp02")
        if ok:
            state[vm] = count + 1
            r["action"] = f"RESUME #{count + 1} ({detail})"
            r["problems"].append(f"{vm}: run_experiment.sh estava morto → RESUME #{count + 1} disparado")
        else:
            r["action"] = "RESUME-FALHOU"
            r["problems"].append(f"{vm}: tentativa de RESUME falhou → {detail}")
    save_state(state)

    # monta a seção markdown do ciclo (ts = hora LOCAL da verificação)
    lines = [f"\n## Ciclo {ts} (local)", ""]
    lines.append("| VM | estado | % | ok | fail | active | remaining | ETA | ação |")
    lines.append("|----|--------|---|----|------|--------|-----------|-----|------|")
    for r in reports:
        eta = r.get("eta")
        eta_s = f"~{eta/3600:.1f}h" if isinstance(eta, (int, float)) and eta else "—"
        lines.append(
            f"| {r['vm']} | {r.get('state','?')} | {r.get('pct',0):.1f}% | "
            f"{r.get('completed','?')} | {r.get('failed','?')} | {r.get('active','?')} | "
            f"{r.get('remaining','?')} | {eta_s} | {r.get('action','—')} |"
        )
    problems = [p for r in reports for p in r["problems"]]
    if problems:
        lines.append("")
        lines.append("**Problemas / eventos:**")
        for p in problems:
            lines.append(f"- {p}")
    else:
        lines.append("")
        lines.append("_Sem problemas neste ciclo._")

    section = "\n".join(lines) + "\n"
    with open(LOG, "a") as fh:
        fh.write(section)

    # ecoa um resumo curto no stdout (vai pro cron.out)
    print(f"[{ts}] " + " | ".join(
        f"{r['vm']}:{r.get('state','?')}({r.get('pct',0):.0f}%)" + (
            f"→{r['action']}" if r.get("action") not in ("—", None) else "")
        for r in reports
    ))


if __name__ == "__main__":
    sys.exit(main())
