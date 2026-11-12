#!/usr/bin/env bash
# Group 5: GATOR runs with the new jar (task 4.1), at most 6 JVMs of 12g at once (72 GB <= 80 GB budget).
E=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax
S=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/scripts/run_gator.sh
BC=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study03-replication-package/data/raw/e6-corpus/org.musicbrainz.picard.barcodescanner_38.apk
CA=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk
cat > $E/scripts/run_new.jobs <<JOBS
$S $E/new/full $BC 12g --full-output
$S $E/new/compact $BC 12g
$S $E/new/d10-full $BC 12g --full-output --dist-max 10
$S $E/new/d10-compact $BC 12g --dist-max 10
$S $E/new/d15-full $BC 12g --full-output --dist-max 15
$S $E/new/d15-compact $BC 12g --dist-max 15
$S $E/new/full $CA 12g --full-output
$S $E/new/compact $CA 12g
$S $E/new/d10-full $CA 12g --full-output --dist-max 10
$S $E/new/d10-compact $CA 12g --dist-max 10
$E/scripts/run_fixture_recipe.sh $E/new/fixture-recipe
JOBS
xargs -P 6 -I{} bash -c '{}' < $E/scripts/run_new.jobs
echo done
