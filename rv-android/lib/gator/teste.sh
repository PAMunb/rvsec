echo "TESTE — RvsecAnalysisClient"

baseDir="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
apk_path=$baseDir"/cryptoapp.apk"
sdk_path="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
client_jar="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator/rvsec-analysis-client.jar"
mop_dir="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca"
results_file="/home/pedro/tmp/cryptoapp.apk.json"
working_dir=$(pwd)

gator_dir=$(dirname "$(readlink -f "$0")")
echo "Gator dir: $gator_dir"

apkname=$(basename $apk_path)

apk_path=$(realpath $apk_path)
sdk_path=$(realpath $sdk_path)

echo "APK path: $apk_path"
echo "Android Sdk path: $sdk_path"
echo "Apk Name: $apkname"
echo "Working dir: $working_dir"
echo "MOP dir: $mop_dir"

START=$(date +%s)
cd "$gator_dir"
./gator a -p $apk_path --client-jar $client_jar --out $results_file -client RvsecAnalysisClient -clientParam mopDir=$mop_dir -withCHA --timeout 600
cd "$working_dir"
END=$(date +%s)
DIFF=$(( $END - $START ))
echo "Processed in $DIFF seconds."
