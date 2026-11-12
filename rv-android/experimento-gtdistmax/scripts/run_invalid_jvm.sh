#!/usr/bin/env bash
# Task 5.5, JVM level: the java command the launcher builds (its --debug mode prints it and keeps the decoded
# resources), run directly so that the JVM's own exit status is observed.
v=$1; out=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/invalid/jvm-$v/cryptoapp.apk.json
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/lib/gator || exit 127
javacmd=$(/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/.venv/bin/python ./gator a -d -p /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk --client-jar /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/lib/gator/rvsec-analysis-client.jar --out "$out" \
  -client RvsecAnalysisClient -clientParam mopDir=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rvsec/rvsec-mop/src/main/resources/jca_android -cgAlgorithm spark \
  --timeout 600 --jvm-memory 12G -clientParam codePackage=br.unb.cic.cryptoapp -clientParam codePackageSource=manifest \
  -clientParam fullOutput=true -cgDelegation true -clientParam "distMax=$v" | grep '^\.\.\.\.\.\. java ' | sed 's/^\.\.\.\.\.\. //')
echo "$javacmd" > /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/invalid/jvm-$v.cmd
start=$(date +%s.%N)
$javacmd > /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/invalid/jvm-$v.log 2>&1
rc=$?
end=$(date +%s.%N)
LC_ALL=C printf 'JVM distMax=%s exit=%s wall=%.1fs output_file_exists=%s\n' "$v" $rc "$(echo "$end - $start" | bc)" $([ -e "$out" ] && echo yes || echo no)
