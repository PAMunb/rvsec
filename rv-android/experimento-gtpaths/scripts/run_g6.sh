#!/usr/bin/env bash
# Group 6 runs with the new jar: every APK in full, compact and compact+paths; full+paths on
# cryptoapp and cry.otp; a second compact+paths run of cry.otp (INV-ANA-92). At most 6 JVMs of
# 12g at a time (72 GB, under the 80 GB heap budget).
set -u
W=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/paths/rv-android
C=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study03-replication-package/data/raw/e6-corpus
S=$W/experimento-gtpaths/scripts/run_gator.sh
N=$W/experimento-gtpaths/new
apk() { case $1 in cryptoapp) echo "$W/apks_examples/cryptoapp.apk";; *) echo "$C/$1.apk";; esac; }
APKS="cryptoapp net.gaast.giggity_769 org.cry.otp_31 org.fedorahosted.freeotp_48 com.vrem.wifianalyzer_71 systems.sieber.droid_scep_7"
jobs_list=()
for a in $APKS; do
  jobs_list+=("full|$a|--full-output" "compact|$a|" "compact-paths|$a|--distance-paths")
done
jobs_list+=("full-paths|cryptoapp|--full-output --distance-paths" "full-paths|org.cry.otp_31|--full-output --distance-paths" "compact-paths-rerun|org.cry.otp_31|--distance-paths")
for j in "${jobs_list[@]}"; do
  IFS='|' read -r cfg a extra <<<"$j"
  while [ "$(jobs -rp | wc -l)" -ge 6 ]; do wait -n; done
  # shellcheck disable=SC2086
  "$S" "$N/$cfg" "$(apk "$a")" 12g $extra &
done
wait
