#!/usr/bin/env python3
"""Os seis portões do smoke da comp162. É o critério de aceitação, não o `up -d`.

    uv run python scripts/smoke_gates.py

Os portões 3 e 4 leem o `RUN_START` do traço NDJSON, e não o log do container. O
`ape.properties` é efêmero no dispositivo e nunca chega ao log; o `RUN_START` é o que o
*jar* resolveu, que é a pergunta real. Um jar anterior ao stage 2 trata `ape.preset` como
chave desconhecida e todos os braços colapsam para os defaults do Config — com o diretório
de resultados ainda carregando o nome do braço. O `RUN_START` é o único lugar onde essa
falha aparece.

O discriminador do portão 3 é a lista `features` — o que o jar resolveu ligar — e não o eco
dos pesos em `params`, que é seletivo: o jar omite do eco toda chave que já está no próprio
default. As duas listas esperadas são as da perna B da gh97, campanha já validada, então o
portão pergunta "este braço resolveu igual ao que passou no portão empírico?", que é mais
forte do que qualquer asserção escrita à mão aqui.

Adaptado de `data/results/cmp163_smoke_gates.py`. Duas mudanças: o corpus é o
`selected162`, e o portão 7 é novo — ele confere que a guarda INV-APV-60 está *dentro* da
imagem, que é a razão de a imagem ter sido reconstruída.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent

RES = EXP / "results_smoke"
CONTAINERS = ["comp162smoke_00", "comp162smoke_01"]
TIMEOUT = 120
TEARDOWN_GRACE = 45  # APERV_TEARDOWN_GRACE_S
FULL_TIMEOUT = 300  # o orçamento da campanha, para a extrapolação do ciclo
MANIFEST = json.loads((EXP / "manifest.json").read_text())
CORPUS = MANIFEST["corpus"]["corpus_basis"]
IMAGE = MANIFEST["image"]["tag"]
EXPECTED_IDENTITIES = 6

# O lote mais cheio da campanha, para a projeção de wall-clock.
BIGGEST_BATCH_RUNS = 21 * 3 * 3

fails: list[int] = []


def gate(n, title, ok, evidence):
    print(f"[{'PASS' if ok else 'FAIL'}] Portão {n} — {title}")
    for line in evidence:
        print(f"        {line}")
    if not ok:
        fails.append(n)
    print()


# Identidade, nunca registro: o resume acrescenta em vez de sobrescrever, então uma
# identidade recuperada guarda dois registros.
by_ident: dict[tuple, tuple[str, dict]] = {}
for c in CONTAINERS:
    p = RES / c / c / "tasks.json"
    if not p.exists():
        print(f"!! tasks.json ausente: {p}")
        continue
    doc = json.loads(p.read_text())
    for t in (doc["tasks"] if isinstance(doc, dict) else doc):
        cfg, res = t["config"], t["result"]
        tc = cfg["tool_config"]
        ident = (cfg["apk_name"], tc["name"], tc.get("variant"), cfg["repetition"], cfg["timeout"])
        if ident not in by_ident or res.get("state") == "COMPLETED":
            by_ident[ident] = (c, res)

print(f"identidades distintas: {len(by_ident)}\n")


def artifact(container, res, key):
    """Resolve um caminho gravado em tasks.json (relativo a results/) no host."""
    rel = res.get(key) or ""
    return RES / container / rel.replace("results/", "", 1) if rel else None


def run_start(container, res):
    tf = artifact(container, res, "trace_file")
    if not tf or not tf.exists():
        return None
    with tf.open(errors="ignore") as fh:
        line = fh.readline()
    try:
        rec = json.loads(line)
    except Exception:
        return None
    return rec if rec.get("type") == "RUN_START" else None


# --- Portão 1 ---------------------------------------------------------------
completed = [(i, r) for i, (_, r) in by_ident.items() if r.get("state") == "COMPLETED"]
clean = [(i, r) for i, r in completed if not r.get("error_message")]
gate(1, f"{EXPECTED_IDENTITIES}/{EXPECTED_IDENTITIES} identidades COMPLETED, error_message vazio",
     len(by_ident) == EXPECTED_IDENTITIES and len(clean) == EXPECTED_IDENTITIES,
     [f"identidades={len(by_ident)} COMPLETED={len(completed)} limpas={len(clean)}"]
     + [f"{i[1]}:{i[2] or '':<16} {i[0][:34]:<34} {r.get('state')} {r.get('error_message') or ''}"
        for i, (_, r) in sorted(by_ident.items())])

# --- Portão 2 ---------------------------------------------------------------
ev, ok = [], True
for ident, (_, r) in sorted(by_ident.items()):
    m = r.get("coverage_metrics") or {}
    cm, ca = m.get("method_coverage", 0), m.get("activities_coverage", 0)
    ok &= cm > 0 and ca > 0
    ev.append(f"{ident[1]}:{ident[2] or '':<16} {ident[0][:30]:<30} "
              f"cov_method={cm:6.2f} cov_act={ca:6.2f} "
              f"cov_mop={m.get('methods_mop_reachable_coverage', 0):6.2f} "
              f"errors={m.get('total_errors', 0)}")
gate(2, "cov_method > 0 e cov_act > 0 em todos os braços", ok, ev)

# --- Portões 3 e 4: o RUN_START confirma o braço que o jar resolveu ---------
expected_features = {
    "mop_off_llm_off": {
        "ACTIVITY_BUDGET", "COVERAGE_BOOST", "DYNAMIC_EPSILON", "FOREIGN_ACTIVITY_GUARD",
        "FORM_COMPLETION", "FRONTIER", "FUZZING", "HEURISTIC_INPUT",
        "LEAST_VISITED_TIEBREAK", "MODEL_MENU", "MOP", "MOP_ACTIVITY_SOURCE",
        "TREE_ENHANCEMENTS", "TREE_PACKAGE_GUARD", "TYPED_FUZZ",
    },
    "mop_on_llm_off": {
        "ACTIVITY_BUDGET", "ACTIVITY_TRIGGER", "COVERAGE_BOOST", "DYNAMIC_EPSILON",
        "FOREIGN_ACTIVITY_GUARD", "FORM_COMPLETION", "FRONTIER", "FUZZING",
        "HEURISTIC_INPUT", "LEAST_VISITED_TIEBREAK", "MENU_GATEWAY", "MODEL_MENU",
        "MOP", "MOP_ACTIVITY_SOURCE", "MOP_FRONTIER", "TREE_ENHANCEMENTS",
        "TREE_PACKAGE_GUARD", "TYPED_FUZZ", "WTG",
    },
}

ev3, ev4 = [], []
ok3 = ok4 = True
seen_props_digests: dict[str, set] = {}
for ident, (c, r) in sorted(by_ident.items()):
    if ident[1] != "aperv":
        continue
    variant = ident[2]
    rs = run_start(c, r)
    if rs is None:
        ev3.append(f"{variant}: RUN_START AUSENTE ou ilegível no traço")
        ok3 = ok4 = False
        continue
    params = rs.get("params", {})
    seen_props_digests.setdefault(variant, set()).add(rs.get("props_digest"))

    feats = set(rs.get("features", []))
    want = expected_features[variant]
    good = rs.get("preset") == "mop" and rs.get("agent") == "sata" and feats == want
    if variant == "mop_off_llm_off":
        # A guia desligada tem que ser visível como peso zerado, e a navegação tem que
        # sobreviver (INV-APV-30).
        good &= params.get("ape.mopWeightDirect") == 0 and params.get("ape.frontierBoostWeight") == 200
    else:
        good &= params.get("ape.mopFrontierWeight") == 200 and params.get("ape.activityTriggerEnabled") is True
    ok3 &= good
    missing, extra = sorted(want - feats), sorted(feats - want)
    ev3.append(f"{variant}: preset={rs.get('preset')} agent={rs.get('agent')} "
               f"features={len(feats)}/{len(want)}"
               + (f" FALTAM={missing}" if missing else "")
               + (f" SOBRAM={extra}" if extra else "")
               + f" -> {'ok' if good else 'INESPERADO'}")
    ev3.append(f"   build.sha={(rs.get('build') or {}).get('sha')} "
               f"props_digest={str(rs.get('props_digest'))[:16]}… "
               f"corpus_basis={'ok' if rs.get('corpus_basis') == CORPUS else 'DIVERGE: ' + str(rs.get('corpus_basis'))}")
    if rs.get("corpus_basis") != CORPUS:
        ok3 = False

    has_path = params.get("ape.mopDataPath") == "/data/local/tmp/mop-artifact.json"
    ok4 &= has_path
    ev4.append(f"{variant}: ape.mopDataPath={params.get('ape.mopDataPath')}")

# Os dois braços têm que diferir no props_digest — se baterem, é o mesmo braço rodando
# duas vezes sob nomes diferentes.
if len(seen_props_digests) == 2:
    a, b = seen_props_digests.values()
    distinct = not (a & b)
    ok3 &= distinct
    ev3.append(f"props_digest distintos entre os dois braços: {distinct}")

gate(3, "RUN_START: preset resolvido e deltas do braço corretos (jar stage-4)", ok3, ev3)
gate(4, "ape.mopDataPath presente nos dois braços aperv", ok4, ev4)

# --- Portão 5 ---------------------------------------------------------------
ev5, ok5 = [], True
for ident, (c, r) in sorted(by_ident.items()):
    if ident[1] != "ape":
        continue
    tf = artifact(c, r, "trace_file")
    size = tf.stat().st_size if tf and tf.exists() else -1
    m = r.get("coverage_metrics") or {}
    good = size > 0 and (m.get("method_coverage") or 0) > 0
    ok5 &= good
    ev5.append(f"{ident[0][:34]:<34} trace={size} bytes cov_method={m.get('method_coverage', 0):.2f}")
gate(5, "braço ape: cobertura > 0 e trace não vazio", ok5, ev5)

# --- Portão 6 ---------------------------------------------------------------
ve = []
for c in CONTAINERS:
    for p in (RES / c).rglob("*.logcat"):
        n = p.read_text(errors="ignore").count("VerifyError")
        if n:
            ve.append(f"{p.name}: {n}")
gate(6, "zero VerifyError de carga (instrumentação nova)", not ve,
     ve or ["nenhum VerifyError em nenhum logcat"])

# --- Portão 7: a guarda INV-APV-60 está DENTRO da imagem --------------------
# É a razão de a imagem ter sido reconstruída. Sem ela, exploração truncada é gravada
# COMPLETED com error_message vazio e o resume não a alcança — na cmp163 isso custou um
# script de reparo offline e um APK que truncou duas vezes sem ser detectado na hora.
# O teste é sobre a imagem, não sobre a árvore do host: o container roda o código que a
# imagem carrega, e o bind-mount desta campanha cobre só o jar.
probe = subprocess.run(
    ["docker", "run", "--rm", "--entrypoint", "grep", IMAGE, "-c", "INV-APV-60",
     "/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py"],
    capture_output=True, text=True,
)
hits = probe.stdout.strip() or "0"
gate(7, "guarda INV-APV-60 presente na imagem", probe.returncode == 0 and int(hits) > 0,
     [f"imagem={IMAGE}", f"ocorrências de INV-APV-60 em tool.py: {hits}",
      "(0 => a imagem é anterior a c1d28365; truncamento silencioso volta a ser possível)"])

# --- Calibração do ciclo (não bloqueante) ----------------------------------
print("--- ciclo por run (calibra o wall-clock da corrida completa) ---")
els = []
floor = TIMEOUT - TEARDOWN_GRACE
for ident, (_, r) in sorted(by_ident.items()):
    el = r.get("execution_time_seconds")
    if not el:
        continue
    els.append(el)
    flag = "" if el >= floor else f"  << ABAIXO DO PISO ({floor}s)"
    print(f"  {ident[1]}:{ident[2] or '':<16} {el:>5} s  {ident[0][:34]}{flag}")
if els:
    over = sum(els) / len(els) - TIMEOUT
    cycle = FULL_TIMEOUT + over
    print(f"  média {sum(els)/len(els):.1f} s para orçamento de {TIMEOUT} s -> sobrecarga ~{over:.1f} s/run")
    print(f"  => ciclo projetado a {FULL_TIMEOUT} s: {cycle:.0f} s/run")
    print(f"  => 8 containers, lote maior de 21 APKs x 3 braços x 3 reps = "
          f"{BIGGEST_BATCH_RUNS} runs: {BIGGEST_BATCH_RUNS * cycle / 3600:.1f} h")
    print(f"     (referência da cmp163 no mesmo host: 370 s/run -> "
          f"{BIGGEST_BATCH_RUNS * 370 / 3600:.1f} h)")

print()
if fails:
    print(f"SMOKE REPROVADO — portões que falharam: {fails}")
    sys.exit(1)
print("SMOKE APROVADO — todos os sete portões passaram")
