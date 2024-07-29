APK=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk


java -jar soot-infoflow-cmd-2.13.0-jar-with-dependencies.jar \
    -a $APK \
    -p /home/pedro/desenvolvimento/aplicativos/android/platforms-sable \
    -s SourcesAndSinks.txt \
    -o resultado -ac /home/pedro/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar