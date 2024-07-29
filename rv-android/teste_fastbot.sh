adb -s emulator-5554 install -r /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/cryptoapp.apk

adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/monkeyq.jar /sdcard/monkeyq.jar
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/fastbot-thirdpart.jar /sdcard/fastbot-thirdpart.jar
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/framework.jar /sdcard/framework.jar
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/libs/arm64-v8a/libfastbot_native.so /data/local/tmp/arm64-v8a/libfastbot_native.so
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/libs/armeabi-v7a/libfastbot_native.so /data/local/tmp/armeabi-v7a/libfastbot_native.so
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/libs/x86/libfastbot_native.so /data/local/tmp/x86/libfastbot_native.so
adb push /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tools/fastbot/libs/x86_64/libfastbot_native.so /data/local/tmp/x86_64/libfastbot_native.so

aapt2 dump strings /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/cryptoapp.apk > max.valid.strings

adb -s emulator-5554 shell CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jarexec app_process /system/bin com.android.commands.monkey.Monkey -p br.unb.cic.cryptoapp --agent reuseq --running-minutes 120 --throttle 200 -v -v
