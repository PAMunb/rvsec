#!/bin/sh

#APK=osmtracker.apk
#APK=apks/media.apk
#APK=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/media.apk
#APK=cryptoapp.apk
#APK=media.apk


#APK=apks/ar.rulosoft.mimanganu_75.apk
APK=apks/at.bitfire.davdroid_403060100.apk
#APK=apks/ch.protonvpn.android_604074100.apk
#APK=apks/com.btcontract.wallet_97.apk
#APK=apks/com.commonslab.commonslab_3.apk
#APK=apks/com.eletac.tronwallet_11.apk
#APK=apks/com.example.openpass_1.apk
#APK=apks/com.iboalali.sysnotifsnooze_102.apk
#APK=apks/com.ichi2.anki_21605300.apk
#APK=apks/com.infomaniak.drive_40202501.apk
#APK=apks/com.infomaniak.mail_10001201.apk
#APK=apks/com.maxfierke.sandwichroulette_2.apk
#APK=apks/com.nextcloud.android.beta_20230906.apk
#APK=apks/com.nhellfire.kerneladiutor_248.apk
#APK=apks/com.outdoordevs.ellaism.wallet_35.apk
#APK=apks/com.owncloud.android_41000000.apk
#APK=apks/com.quaap.primary_33.apk
#APK=apks/com.ruesga.android.wallpapers.photophase_1036.apk
#APK=apks/com.valleytg.oasvn.android_11.apk
#APK=apks/com.vitorpamplona.amethyst_293.apk
#APK=apks/de.fmaul.android.cmis_8.apk



APK_NAME="$(basename $APK)"

MOP_DIR=mop
#MOP_DIR=mop_mini

#./generate_monitor.sh $MOP_DIR mop_out

./instrument.sh $APK mop_out out

echo "[+] Done! Final apk generated in out/$APK_NAME"
