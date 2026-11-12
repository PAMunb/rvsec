#!/usr/bin/env bash
# Task 0.2: baseline GATOR runs (jars of task 0.1), 4 in parallel at 12g each (48 GB <= 80 GB budget)
S=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/scripts/run_gator.sh
$S /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/baseline/compact /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk 12g &
$S /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/baseline/compact /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study03-replication-package/data/raw/e6-corpus/org.musicbrainz.picard.barcodescanner_38.apk 12g &
$S /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/baseline/full /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk 12g --full-output &
$S /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/baseline/full /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study03-replication-package/data/raw/e6-corpus/org.musicbrainz.picard.barcodescanner_38.apk 12g --full-output &
wait
echo done
