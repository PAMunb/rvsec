#!/usr/bin/env bash
# Task 5.5: the GATOR jar called directly (the command get_tool_command builds, as in the 5.1 log) with an invalid distMax.
v=$1; out=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/invalid/direct-$v/cryptoapp.apk.json
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/lib/gator || exit 127
start=$(date +%s.%N)
/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/.venv/bin/python ./gator a -p /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk --client-jar /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/lib/gator/rvsec-analysis-client.jar --out "$out" \
  -client RvsecAnalysisClient -clientParam mopDir=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rvsec/rvsec-mop/src/main/resources/jca_android -cgAlgorithm spark \
  --timeout 600 --jvm-memory 12G -clientParam codePackage=br.unb.cic.cryptoapp -clientParam codePackageSource=manifest \
  -clientParam fullOutput=true -cgDelegation true -clientParam "distMax=$v" > /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/invalid/direct-$v.log 2>&1
rc=$?
end=$(date +%s.%N)
LC_ALL=C printf 'distMax=%s exit=%s wall=%.1fs output_file_exists=%s output_dir_exists=%s\n' "$v" $rc "$(echo "$end - $start" | bc)" \
  $([ -e "$out" ] && echo yes || echo no) $([ -e "$(dirname "$out")" ] && echo yes || echo no)
