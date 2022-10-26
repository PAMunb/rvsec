#!/bin/sh

#APK=osmtracker.apk
#APK=media.apk
#APK=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/media.apk



##### - works
###   - error, but "works"
#     - error


#APK=14-30-com.vecturagames.android.app.passwordgenerator_35.apk -->  instrumenting: Type 'kotlin.jvm.functions.Function3' (no debug info available) [error] Mismatch when building parameterization map...
APK=apks/21-30-com.hwloc.lstopo_266.apk
#APK=21-31-org.alberto97.ouilookup_14.apk --> d8: Merging dex file containing classes with prefix 'j$.' with classes with any other prefixes is not allowed.
#APK=24-30-com.blogspot.e_kanivets.moneytracker_36.apk --> instrumenting: java.lang.IllegalStateException: Unexpected problem whilst preparing bytecode for com.dropbox.core.v2.teamlog.EventDetails$Serializer.deserialize(Lcom/fasterxml/jackson/core/JsonParser;)Lcom/dropbox/core/v2/teamlog/EventDetails;
##### APK=26-29-app.zeusln.zeus_25.apk
#APK=ademar.bitac_5.apk --> dex2jar: java.lang.StringIndexOutOfBoundsException: String index out of range: -2
#APK=com.btcontract.wallet_86.apk --> instrumenting: GC overhead limit
#APK=com.coinerella.peercoin_106.apk --> adb install: Failure [INSTALL_FAILED_NO_MATCHING_ABIS: Failed to extract native libraries, res=-113]
#APK=com.emanuelef.remote_capture_60.apk --> instrumenting: Type 'kotlin.jvm.functions.Function3' (no debug info available) [error] Mismatch when building parameterization map...
#APK=com.gaurav.avnc_14.apk --> dex2jar: java.lang.StringIndexOutOfBoundsException: String index out of range: 44
#APK=com.greenaddress.greenbits_android_wallet.testnet_205.apk --> execution: java.lang.NoClassDefFoundError: Failed resolution of: Lmop/MultiSpec_1MonitorAspect;
### APK=com.marv42.ebt.newnote_5300.apk --> instrumenting, but works
#APK=com.vecturagames.android.app.passwordgenerator_35.apk # --> instrumenting: Type 'kotlin.jvm.functions.Function3' (no debug info available) [error] Mismatch when building parameterization map...
##### APK=de.php_tech.piggybudget_25.apk
#APK=de.salomax.currencies_11703.apk --> execution: java.lang.NoClassDefFoundError: Failed resolution of: Lmop/MultiSpec_1RuntimeMonitor;
#APK=de.varengold.activeTAN_34.apk --> d8: Merging dex file containing classes with prefix 'j$.' with classes with any other prefixes is not allowed.
#APK=hashengineering.darkcoin.wallet_70311.apk --> diversos
#APK=me.hackerchick.catima_92.apk --> d8: Merging dex file containing classes with prefix 'j$.' with classes with any other prefixes is not allowed.
### APK=opencontacts.open.com.opencontacts_24.apk # --> instrumenting, but works
##### APK=org.ebur.debitum_14.apk
##### APK=protect.gift_card_guard_6.apk
##### APK=protect.rentalcalc_6.apk
##### APK=ru.valle.btc_260.apk
##### APK=threads.server_272.apk
#APK=xyz.hisname.fireflyiii_112.apk -->  instrumenting: Type 'kotlin.jvm.functions.Function3' (no debug info available) [error] Mismatch when building parameterization map...


./mop.sh $APK mop 