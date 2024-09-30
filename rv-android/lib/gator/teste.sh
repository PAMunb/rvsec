echo "TESTE"

baseDir="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini"
apk_path=$baseDir"/cryptoapp.apk"
sdk_path="/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms"
client_jar="/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/lib/gator/rvsec-gator-client-0.6.0-SNAPSHOT.jar"
result_dir=$(pwd)
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

#export ANDROID_SDK=$sdk_path

if [ ! -d "$result_dir" ]; then
	mkdir -p "$result_dir"
fi
result_dir=$(realpath $result_dir)
echo "Result dir: $result_dir"

START=$(date +%s)
./gator a -p $apk_path --client-jar $client_jar -client TesteClient #> $result_dir/gator.log
#./gator a -p $apk_path -client WTGDemoClient #> $result_dir/gator.log
END=$(date +%s)
DIFF=$(( $END - $START ))
echo "Processed in $DIFF seconds."  >> $result_dir/gator.log