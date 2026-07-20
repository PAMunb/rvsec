#!/usr/bin/env python3
"""Gera os artefatos de uma comparacao multi-tool no rv-platform.

Saidas (todas com o mesmo --name, para nada ficar solto):
  data/<name>_filters/batch_NN.txt        split round-robin dos APKs (1 por container)
  data/<name>_filters/.gitkeep
  docker/docker-compose.<name>.yml        compose com N containers + SGLang condicional
  docs/<YYYYMMDD>_<name>.md               plano (padrao docs/20260619_comparacao_aperv.md)
  data/results/<name>_compare_meta.json   metadados lidos por monitor/consolidate

Exemplo (comparacao APE x APE-RV, como a de 2026-06-19):
  python3 .claude/skills/rv-experiment-compare/scripts/gen_compare.py \
    --name cmp --dataset /caminho/APKS_FINAL_JCA_DEXLIB_20260604 \
    --tools "ape,aperv:sata,aperv:sata_mop,aperv:sata_mop_llm@llm_percentage=0.9" \
    --timeout 300 --reps 3 --containers 6 --spec-set jca --with-sglang

Exemplo (comparacao sem LLM, sem GPU):
  python3 .../gen_compare.py --name baseline --dataset /caminho/apks \
    --tools "monkey,droidbot:dfs_greedy,aperv:sata" --containers 4
"""
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # rv-android/
SKILL_DIR = Path(__file__).resolve().parents[1]


def list_apks(dataset: Path, avd_abi: str, filter_abi: bool):
    """Lista .apk do dataset, opcionalmente filtrando por ABI compativel com a AVD.

    ABI: em API 30 x86_64 com NDK Translation, sao elegiveis x86_64, arm64-v8a e
    apps sem codigo nativo. Le 'native_code_abis'/'abis' do <apk>.json se existir;
    na ausencia de info, inclui o APK (com aviso)."""
    compat = {"x86_64", "arm64-v8a"} if avd_abi == "x86_64" else {avd_abi}
    apks, skipped, no_info = [], [], 0
    for f in sorted(os.listdir(dataset)):
        if not f.endswith(".apk"):
            continue
        if not filter_abi:
            apks.append(f)
            continue
        meta = dataset / (f + ".json")
        abis = None
        if meta.exists():
            try:
                d = json.loads(meta.read_text())
                abis = d.get("native_code_abis") or d.get("abis") or d.get("native_abis")
            except Exception:
                abis = None
        if abis is None:
            no_info += 1
            apks.append(f)  # sem info -> nao descarta
        elif not abis or (set(abis) & compat):
            apks.append(f)  # sem nativo OU intersecta arch compativel
        else:
            skipped.append(f)
    if filter_abi:
        print(f"[abi] {len(skipped)} APK(s) descartados (arch incompativel com {avd_abi}); "
              f"{no_info} sem info de ABI (incluidos).", file=sys.stderr)
    return apks


def write_filters(apks, n, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = [[] for _ in range(n)]
    for i, a in enumerate(apks):
        groups[i % n].append(a)
    for i, g in enumerate(groups):
        (out_dir / f"batch_{i:02d}.txt").write_text("\n".join(g) + "\n")
    return [len(g) for g in groups]


def gen_compose(args, n):
    has_llm = args.with_sglang
    env = [
        f'    RV_TOOLS: "{args.tools}"',
        f'    RV_TIMEOUTS: "{args.timeout}"',
        f'    RV_REPETITIONS: "{args.reps}"',
        '    RV_NO_WINDOW: "true"',
        f'    RV_SPEC_SET: "{args.spec_set}"',
        '    RV_SKIP_MONITORS: "true"',
        '    RV_SKIP_INSTRUMENT: "true"',
        '    RV_SKIP_STATIC_ANALYSIS: "true"',
        '    RV_APKS_DIR: "/opt/rvsec/rv-android/apks"',
        '    RV_DEVICE_PORT: "5554"',
    ]
    if has_llm:
        env.append('    RVSMART_LLM_MODE: "true"')
    # gh72 — opt-in diagnostics. Emitido APENAS quando --logcat-diagnostics e passado
    # (ato deliberado por campanha, D9); ausente = baseline byte-identico preservado.
    if getattr(args, "logcat_diagnostics", False):
        env.append('    RV_LOGCAT_DIAGNOSTICS: "true"')
    depends = (
        "  depends_on:\n    sglang:\n      condition: service_healthy\n" if has_llm else ""
    )
    L = []
    L.append(f"# Comparacao '{args.name}' — gerado por rv-experiment-compare.")
    L.append(f"# Tools: {args.tools}")
    L.append(f"# {n} containers, timeout {args.timeout}s, {args.reps} reps, specs {args.spec_set}.")
    L.append(f"# Plano: docs/{args.date}_{args.name}.md")
    L.append("# Uso:")
    L.append(f"#   docker compose -f docker/docker-compose.{args.name}.yml up -d")
    L.append(f"#   .claude/skills/rv-experiment-compare/scripts/monitor_compare.sh {args.name}")
    L.append("#   # passada de resume final ao terminar: re-rodar o up -d (recupera FAILED transientes)")
    L.append("#   # NAO dar 'down' antes de extrair traces (artefatos efemeros no device)")
    L.append("")
    L.append("x-rvandroid: &rvandroid-base")
    L.append(f"  image: {args.image}")
    L.append("  environment: &rvandroid-env")
    L += env
    L.append("  devices:")
    L.append("    - /dev/kvm:/dev/kvm")
    L.append("  deploy:")
    L.append("    resources:")
    L.append("      limits:")
    L.append(f'        cpus: "{args.cpus}"')
    L.append(f'        memory: "{args.memory}"')
    if depends:
        L.append(depends.rstrip("\n"))
    L.append("")
    L.append("services:")
    if has_llm:
        L += [
            "  sglang:",
            f"    image: {args.sglang_image}",
            "    container_name: sglang-server",
            "    volumes:",
            f"      - ${{HF_CACHE:-{args.hf_cache}}}:/root/.cache/huggingface",
            "    ipc: host",
            '    shm_size: "16g"',
            "    deploy:",
            "      resources:",
            "        reservations:",
            "          devices:",
            "            - driver: nvidia",
            "              count: 1",
            "              capabilities: [gpu]",
            "    command: >",
            "      python3 -m sglang.launch_server",
            f"      --model-path {args.sglang_model}",
            "      --host 0.0.0.0",
            f"      --port {args.sglang_port}",
            "      --trust-remote-code",
            "      --attention-backend flashinfer",
            "      --tool-call-parser qwen",
            "      --enable-multimodal",
            "      --context-length 8192",
            "    healthcheck:",
            f'      test: ["CMD", "curl", "-f", "http://localhost:{args.sglang_port}/health"]',
            "      interval: 30s",
            "      timeout: 10s",
            "      retries: 10",
            "      start_period: 120s",
            "",
        ]
    for i in range(n):
        nn = f"{i:02d}"
        L += [
            f"  {args.name}_{nn}:",
            "    <<: *rvandroid-base",
            f"    container_name: {args.name}_{nn}",
            "    environment:",
            "      <<: *rvandroid-env",
            f"      RV_EXPERIMENT_NAME: {args.name}_{nn}",
            f'      RV_APKS_FILTER: "/opt/rvsec/rv-android/filters/batch_{nn}.txt"',
            f'      RV_DELAY: "{i * 10}"',
            "    volumes:",
            f"      - {args.dataset}:/opt/rvsec/rv-android/apks:ro",
            f"      - ../data/{args.name}_filters:/opt/rvsec/rv-android/filters:ro",
            f"      - ../data/results/{args.name}_{nn}:/opt/rvsec/rv-android/results",
            "",
        ]
    return "\n".join(L)


def gen_plan(args, n, sizes, n_apks, n_tools, total):
    tmpl = (SKILL_DIR / "templates" / "plan.md.tmpl").read_text()
    arms = "\n".join(f"| {t.strip()} | `{t.strip()}` | ? | ? | ? |" for t in args.tools.split(","))
    sub = dict(
        name=args.name, date=args.date, tools=args.tools, n_tools=n_tools,
        n_apks=n_apks, reps=args.reps, timeout=args.timeout, containers=n,
        total_tasks=total, spec_set=args.spec_set, dataset=args.dataset,
        image=args.image, arms_table=arms,
        sglang=("sim — " + args.sglang_model) if args.with_sglang else "nao",
        sizes=", ".join(str(s) for s in sizes),
    )
    for k, v in sub.items():
        tmpl = tmpl.replace("{{" + k + "}}", str(v))
    return tmpl


def main():
    p = argparse.ArgumentParser(description="Gera artefatos de uma comparacao multi-tool.")
    p.add_argument("--name", required=True, help="prefixo do experimento (containers <name>_NN)")
    p.add_argument("--dataset", required=True, help="dir com .apk (+ .apk.json co-localizado)")
    p.add_argument("--tools", required=True, help="string RV_TOOLS (virgula)")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--containers", type=int, default=6)
    p.add_argument("--spec-set", default="jca")
    p.add_argument("--image", default="phtcosta/rvandroid:0.9.3")
    p.add_argument("--cpus", default="4")
    p.add_argument("--memory", default="10g")
    p.add_argument("--with-sglang", action="store_true", help="inclui servico SGLang (braco LLM)")
    p.add_argument("--sglang-image", default="lmsysorg/sglang:v0.5.6.post2")
    p.add_argument("--sglang-model", default="Qwen/Qwen3-VL-4B-Instruct")
    p.add_argument("--sglang-port", type=int, default=30000)
    p.add_argument("--hf-cache", default="/pedro/desenvolvimento/.cache/huggingface")
    p.add_argument("--avd-abi", default="x86_64")
    p.add_argument("--filter-abi", action="store_true", help="filtra APKs por ABI compativel (le .apk.json)")
    p.add_argument(
        "--logcat-diagnostics",
        action="store_true",
        help=(
            "liga a captura opt-in de eventos diagnosticos (crashes/VerifyError/ANR) "
            "-> RV_LOGCAT_DIAGNOSTICS=true + app_events.csv (gh72). Default OFF: "
            "captura byte-identica ao baseline RVSEC/RVSEC-COV (D9). Ligar e ato "
            "deliberado por campanha."
        ),
    )
    p.add_argument("--force", action="store_true", help="sobrescreve artefatos existentes")
    args = p.parse_args()
    args.date = datetime.now().strftime("%Y%m%d")

    dataset = Path(args.dataset)
    if not dataset.is_dir():
        sys.exit(f"dataset inexistente: {dataset}")

    apks = list_apks(dataset, args.avd_abi, args.filter_abi)
    if not apks:
        sys.exit("nenhum .apk encontrado no dataset")
    n = min(args.containers, len(apks))
    n_tools = len([t for t in args.tools.split(",") if t.strip()])
    total = n_tools * len(apks) * args.reps

    filters_dir = ROOT / "data" / f"{args.name}_filters"
    compose_path = ROOT / "docker" / f"docker-compose.{args.name}.yml"
    plan_path = ROOT / "docs" / f"{args.date}_{args.name}.md"
    meta_path = ROOT / "data" / "results" / f"{args.name}_compare_meta.json"

    for path in (compose_path, plan_path):
        if path.exists() and not args.force:
            sys.exit(f"ja existe (use --force): {path}")

    sizes = write_filters(apks, n, filters_dir)
    compose_path.parent.mkdir(parents=True, exist_ok=True)
    compose_path.write_text(gen_compose(args, n))
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(gen_plan(args, n, sizes, len(apks), n_tools, total))
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(dict(
        name=args.name, tools=[t.strip() for t in args.tools.split(",") if t.strip()],
        n_tools=n_tools, reps=args.reps, timeout=args.timeout, containers=n,
        n_apks=len(apks), total_tasks=total, dataset=str(dataset),
        with_sglang=args.with_sglang, filters_dir=str(filters_dir),
    ), indent=2))

    print(f"OK — comparacao '{args.name}' gerada:")
    print(f"  filtros : {filters_dir}/batch_00..{n-1:02d}.txt  ({len(apks)} APKs, sizes {sizes})")
    print(f"  compose : {compose_path}")
    print(f"  plano   : {plan_path}")
    print(f"  meta    : {meta_path}")
    print(f"  total de tasks: {n_tools} tools x {len(apks)} APKs x {args.reps} reps = {total}")
    print(f"\nProximo: revisar o plano, depois:")
    print(f"  docker compose -f docker/docker-compose.{args.name}.yml up -d")


if __name__ == "__main__":
    main()
