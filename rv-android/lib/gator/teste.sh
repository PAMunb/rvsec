echo "TESTE"

baseDir="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
apk_path=$baseDir"/cryptoapp.apk"
sdk_path="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
client_jar="/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator/rvsec-gator-client.jar"
results_file="/home/pedro/tmp/rvsec-gator.json"
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

START=$(date +%s)
./gator a -p $apk_path --client-jar $client_jar --out $results_file -client RvsecWtgClient #> $result_dir/gator.log
#./gator a -p $apk_path -client WTGDemoClient #> $result_dir/gator.log
END=$(date +%s)
DIFF=$(( $END - $START ))
echo "Processed in $DIFF seconds."
