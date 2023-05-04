#!/bin/sh

# emulator must be running ... (sh run_emulator.sh)


#APK=media.apk
APK=21-30-com.hwloc.lstopo_266.apk
# sudo apt install aapt
# aapt dump badging media.apk | grep package:\ name
#OR
# adb shell
# pm list packages -f
#PACKAGE_NAME="com.example.myapp"
PACKAGE_NAME="com.hwloc.lstopo"


#./mop.sh apks/$APK mop

#./generate_monitor.sh mop mop_out

./instrument.sh apks/$APK mop mop_out


echo "[+] Installing APK"
adb install out/$APK

echo "[+] Running droidbot"
#droidbot -d emulator-5554 -a /data/app/com.example.myapp-1.apk -policy monkey -is_emulator -timeout 60
droidbot -d emulator-5554 -a out/$APK -policy monkey -is_emulator -timeout 60