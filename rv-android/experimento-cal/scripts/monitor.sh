#!/bin/bash
# RUN+MONITOR — cadence status + resume policy for one calibration iteration.
#
# Usage: monitor.sh <iter-dir> [--no-resume]
#   <iter-dir>   path to experimento-cal/iterN/ (holds manifest.json, filters/, results/,
#                and docker-compose.<phase>.yml). Container names are <phase>_NN.
#   --no-resume  observe only: report progress, never restart or re-enter any container.
#
# WHAT THIS SCRIPT MEASURES (INV-CAL-07)
#   Progress is counted as IDENTITY-DISTINCT NON-EMPTY logcats under
#   <iter-dir>/results/<phase>_NN/<phase>_NN/<apk>/<apk>__<rep>__<timeout>__<toolfrag>.logcat .
#   Each such file's (apk, rep, timeout, toolfrag) tuple is a distinct identity, and toolfrag
#   already encodes tool+variant ("ape" or "aperv:<variant>"), so the identity
#   (apk, tool, variant, rep, timeout) is fully determined by the file path. We NEVER count
#   the string "COMPLETED" (it double-counts via result.state_transitions[]) and NEVER trust
#   task-state tallies alone. A resume rewrites the SAME logcat path, so counting distinct
#   identities is inherently idempotent.
#   Per-container total = |batch_NN.txt| APKs x n_arms x reps (from manifest.json).
#
# RESUME POLICY (INV-CAL-06)
#   * Exit code 137 (OOM): `docker restart` that container ONLY — standing authorization.
#     On restart the platform resumes (skips COMPLETED identities, re-runs the failed ones).
#   * Exit code 0 but incomplete (ERROR/FAILED tasks remain): a RESUME PASS via
#     `docker compose up -d <service>` re-entry brings the exited-0 container back so the
#     platform re-runs its failed identities.
#   * Exit with ANY OTHER code (crash), or `Up` with NO progress since the previous cadence
#     (stall): REPORTED ONLY, never auto-restarted — a crashed/hung container is a human
#     decision. Experiment configuration is NEVER altered mid-run.
#   `--no-resume` gates BOTH the OOM restart and the resume pass: with it, nothing is touched.
#   Idempotent: safe to run every cadence (e.g. from cron).
#
# WHAT THIS SCRIPT CANNOT DO (manual / other-gate checks it does not replace)
#   * It CANNOT prove the served model. That the SGLang backend actually serves
#     Qwen/Qwen3-VL-4B-Instruct is proven by the SMOKE gate via [APE-LLM-CONFIG-ACK]
#     server_model=..., not here.
#   * It CANNOT distinguish a HUNG container from a merely SLOW one. It reports the progress
#     delta since the previous cadence and leaves every non-137 stall for a human decision;
#     it will not kill or restart a stalled/crashed container.
#   * It CANNOT judge task correctness (VerifyError, coverage>0, config-ack fields) — that is
#     the SMOKE and VERIFY gates. It only counts non-empty logcats, not their contents.
#   * It does NOT manage emulators — rv-platform owns that lifecycle (INV-CAL-13). The only
#     container mutation it performs is `docker restart` (137) and the gated resume pass.
#
# DRY-RUN: with MONITOR_DRYRUN=1 set, or when the `docker` binary is absent, all docker
# calls (ps/inspect/restart/compose) are skipped; the counting + completion logic still runs
# and prints. Container state shows "dryrun" and no resume action is taken.
set -euo pipefail

# ---- arguments ------------------------------------------------------------------------
ITER_DIR="${1:?usage: monitor.sh <iter-dir> [--no-resume]}"
RESUME=1
[ "${2:-}" = "--no-resume" ] && RESUME=0
ITER_DIR="$(cd "$ITER_DIR" && pwd)"          # absolute

MANIFEST="$ITER_DIR/manifest.json"
[ -f "$MANIFEST" ] || { echo "manifest not found: $MANIFEST (run gen_iteration.py first)"; exit 1; }

# ---- dry-run detection ----------------------------------------------------------------
# Docker is skipped when explicitly requested OR when the binary is unavailable. The
# counting/completion path runs regardless, so the script is testable without docker.
DRYRUN=0
[ "${MONITOR_DRYRUN:-}" = "1" ] && DRYRUN=1
command -v docker >/dev/null 2>&1 || DRYRUN=1

# ---- phase + compose file (derived from the iter-dir) ---------------------------------
PHASE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["phase"])' "$MANIFEST")"
COMPOSE="$ITER_DIR/docker-compose.${PHASE}.yml"

STATE="/tmp/cal_monitor_$(printf '%s' "$ITER_DIR" | md5sum | cut -c1-16)_prev.txt"

echo "===== ${PHASE} @ ${ITER_DIR}: $(date '+%Y-%m-%d %H:%M:%S') ====="
if [ "$DRYRUN" -eq 1 ]; then
  echo "[dry-run] docker calls skipped (MONITOR_DRYRUN=1 or docker absent)"
else
  docker ps -a --filter "name=${PHASE}_" --format '{{.Names}} {{.Status}}' | sort || true
  docker ps --filter "name=sglang-server" --format '{{.Names}} {{.Status}}' 2>/dev/null || true
fi
echo

# ---- per-container identity-distinct completion counts --------------------------------
# Emits one "nn done total" line per container. `done` = distinct non-empty-logcat
# identities; `total` = |batch_nn| x n_arms x reps.
python3 - "$ITER_DIR" "$MANIFEST" <<'PY' > "/tmp/cal_monitor_done_now.txt"
import json, sys, os, glob

iter_dir, manifest_path = sys.argv[1], sys.argv[2]
m = json.load(open(manifest_path))
phase = m["phase"]
n_arms = len(m["arms"])
reps = int(m["reps"])
containers = int(m["containers"])

def identity_from_logcat(path):
    # <apk>__<rep>__<timeout>__<toolfrag>.logcat  (toolfrag may contain a ':').
    stem = os.path.basename(path)[: -len(".logcat")]
    parts = stem.split("__", 3)          # apk, rep, timeout, toolfrag
    if len(parts) != 4:
        return None
    apk, rep, timeout, toolfrag = parts
    return (apk, rep, timeout, toolfrag) # toolfrag encodes tool+variant -> full identity

for i in range(containers):
    nn = f"{i:02d}"
    cname = f"{phase}_{nn}"
    # results/<phase>_NN/<phase>_NN/<apk>/<file>.logcat (nested by RV_EXPERIMENT_NAME).
    res_root = os.path.join(iter_dir, "results", cname)
    seen = set()
    for lc in glob.glob(os.path.join(res_root, "**", "*.logcat"), recursive=True):
        try:
            if os.path.getsize(lc) <= 0:      # empty logcat != completed identity
                continue
        except OSError:
            continue
        ident = identity_from_logcat(lc)
        if ident is not None:
            seen.add(ident)
    done = len(seen)
    batch = os.path.join(iter_dir, "filters", f"batch_{nn}.txt")
    apks = 0
    if os.path.exists(batch):
        apks = sum(1 for ln in open(batch) if ln.strip() and not ln.strip().startswith("#"))
    total = apks * n_arms * reps
    print(nn, done, total)
PY

# ---- classify + act per container -----------------------------------------------------
declare -A PREV
[ -f "$STATE" ] && while read -r k v; do PREV[$k]="$v"; done < "$STATE"

NEW="$(mktemp)"; gtot=0; gdone=0
actions=""            # OOM restarts already applied
resume_svcs=""        # exit-0 incomplete containers -> single resume-pass compose up
reports=""            # human-decision items (crashes, stalls)

while read -r nn done total; do
  cname="${PHASE}_${nn}"
  prev="${PREV[$nn]:- -1}"
  flag=""

  if [ "$total" -gt 0 ] && [ "$done" -ge "$total" ]; then
    flag="DONE"
  elif [ "$DRYRUN" -eq 1 ]; then
    flag="(dryrun: no docker state)"
  else
    read -r status exitcode running < <(
      docker inspect -f '{{.State.Status}} {{.State.ExitCode}} {{.State.Running}}' "$cname" 2>/dev/null \
        || echo "missing - -"
    )
    if [ "$running" = "true" ]; then
      if [ "$prev" -ge 0 ] 2>/dev/null && [ "$done" -eq "$prev" ]; then
        flag="STALL (no progress; human decision)"
        reports="$reports\n  ${cname}: Up but no progress since last cadence (done=$done) — inspect manually"
      else
        flag="RUNNING"
      fi
    elif [ "$status" = "exited" ] && [ "$exitcode" = "137" ]; then
      if [ "$RESUME" -eq 1 ]; then
        flag="OOM(137) -> restart"
        docker restart "$cname" >/dev/null 2>&1 \
          && actions="$actions\n  ${cname}: docker restart (OOM 137, done=$done<$total)"
      else
        flag="OOM(137) [held: --no-resume]"
      fi
    elif [ "$status" = "exited" ] && [ "$exitcode" = "0" ]; then
      if [ "$RESUME" -eq 1 ]; then
        flag="EXIT0 incomplete -> resume pass"
        resume_svcs="$resume_svcs $cname"
      else
        flag="EXIT0 incomplete [held: --no-resume]"
      fi
    elif [ "$status" = "exited" ]; then
      flag="CRASHED(exit=$exitcode; human decision)"
      reports="$reports\n  ${cname}: exited code $exitcode (not 137) — NOT restarted, inspect manually"
    else
      flag="${status} (human decision)"
      reports="$reports\n  ${cname}: state '$status' — reported only"
    fi
  fi

  pct=0; [ "$total" -gt 0 ] && pct=$((done * 100 / total))
  printf "%s: %5d / %5d identities (%d%%)  %s\n" "$cname" "$done" "$total" "$pct" "$flag"
  echo "$nn $done" >> "$NEW"
  gtot=$((gtot + total)); gdone=$((gdone + done))
done < "/tmp/cal_monitor_done_now.txt"
mv "$NEW" "$STATE"

# ---- resume pass (exit-0 incomplete containers only) ----------------------------------
# One `docker compose up -d <svc...>` re-entry; the platform skips COMPLETED identities and
# re-runs the failed ones. Crashed (non-137) containers are deliberately NOT included.
if [ "$DRYRUN" -eq 0 ] && [ "$RESUME" -eq 1 ] && [ -n "$resume_svcs" ]; then
  # shellcheck disable=SC2086
  if docker compose -f "$COMPOSE" --project-directory "$ITER_DIR" up -d $resume_svcs >/dev/null 2>&1; then
    actions="$actions\n  resume pass (compose up -d):$resume_svcs"
  else
    reports="$reports\n  resume pass FAILED for:$resume_svcs — inspect manually"
  fi
fi

# ---- summary --------------------------------------------------------------------------
gpct=0; [ "$gtot" -gt 0 ] && gpct=$((gdone * 100 / gtot))
echo "-------------------------------------------"
printf "TOTAL: %5d / %5d identity-distinct non-empty logcats (%d%%)\n" "$gdone" "$gtot" "$gpct"
if [ "$gtot" -gt 0 ] && [ "$gdone" -ge "$gtot" ]; then
  echo "VERDICT: COMPLETE (all predicted identities present)"
else
  echo "VERDICT: INCOMPLETE (run in progress or residual failed identities)"
fi

if [ -n "$actions" ]; then echo; echo ">>> RESUME ACTIONS TAKEN:"; echo -e "$actions"; fi
if [ -n "$reports" ]; then echo; echo ">>> REPORTED FOR HUMAN DECISION (no action):"; echo -e "$reports"; fi
[ -z "$actions" ] && [ -z "$reports" ] && { echo; echo ">>> No action needed."; }
