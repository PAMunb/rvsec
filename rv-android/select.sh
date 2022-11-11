#!/bin/sh

# DIRS:
# android-apks: todos os (360+) apks
# apks_pilot: 24 apks do teste piloto
# apks_test: diretório para colocar os apks para executar esse script para verificar a instrumentacao
# apḱs_selecionados: os apks que foram instrumentados

##### - works
###   - error, but "works"
#     - error

BASE_DIR=apks_test

APK=$BASE_DIR/

##### APK=$BASE_DIR/21-30-com.hwloc.lstopo_266.apk
#APK=$BASE_DIR/26-29-app.zeusln.zeus_25.apk --> d8: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/ademar.bitac_5.apk --> dex2jar: java.lang.StringIndexOutOfBoundsException: String index out of range: -2
#APK=$BASE_DIR/anonaddy.apk --> d8: Merging dex file containing classes with prefix 'j$.' with classes with any other prefixes is not allowed
#APK=$BASE_DIR/app.crescentcash.src_120.apk --> d8: Error in tmp/monitored_app.crescentcash.src_120.apk.jar:org/bouncycastle/jcajce/provider/symmetric/CAST5$AlgParamGen.class at Lorg/bouncycastle/jcajce/provider/symmetric/CAST5$AlgParamGen;engineGenerateParameters()Ljava/security/AlgorithmParameters;:
#APK=$BASE_DIR/app.zeusln.zeus_25.apk #--> aspectj: AspectJ Internal Error: unable to add stackmap attributes. -1. Unable to find Asm for stackmap generation (Looking for 'aj.org.objectweb.asm.ClassReader'). Stackmap generation for woven code is required to avoid verify errors on a Java 1.7 or higher runtime
##### APK=$BASE_DIR/aq.metallists.loudbang_45.apk
##### APK=$BASE_DIR/at.bitfire.nophonespam_15.apk
##### APK=$BASE_DIR/at.h4x.metaapp_10102.apk
##### APK=$BASE_DIR/at.zweng.bankomatinfos2_16.apk
#APK=$BASE_DIR/betterschedule.apk --> aspectj: Type 'kotlin.jvm.functions.Function1' (no debug info available) [error] Mismatch when building parameterization map.
##### APK=$BASE_DIR/bilidownload.apk
##### APK=$BASE_DIR/bluepie.ad_silence_11.apk
#APK=$BASE_DIR/cheogram.apk --> d8: Error in tmp/monitored_cheogram.apk.jar:eu/siacs/conversations/ui/MagicCreateActivity.class at Leu/siacs/conversations/ui/MagicCreateActivity;lambda$onCreate$0(Landroid/view/View;)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/ch.protonvpn.android_102119009.apk --> dex2jar: java.lang.StringIndexOutOfBoundsException: String index out of range: -2
#APK=$BASE_DIR/ch.rmy.android.http_shortcuts_1102120001.apk --> d8: Error in tmp/monitored_ch.rmy.android.http_shortcuts_1102120001.apk.jar:d/a/a/a/m/h/b/o.class at Ld/a/a/a/m/h/b/o;call()Ljava/lang/Object;: java.lang.ArrayIndexOutOfBoundsException: -1
##### APK=$BASE_DIR/cityfreqs.com.pilfershushjammer_41.apk
##### APK=$BASE_DIR/cloud.valetudo.companion_7.apk
##### APK=$BASE_DIR/co.garmax.materialflashlight_29.apk
##### APK=$BASE_DIR/co.timsmart.vouchervault_22.apk
##### APK=$BASE_DIR/com.aaronjwood.portauthority_63.apk
##### APK=$BASE_DIR/com.activitymanager_414.apk
##### APK=$BASE_DIR/com.aidinhut.simpletextcrypt_12.apk
##### APK=$BASE_DIR/com.alaskalinuxuser.justcraigslist_10.apk
#APK=$BASE_DIR/com.android.keepass_203.apk --> d8: Error in tmp/monitored_com.android.keepass_203.apk.jar:org/spongycastle/jcajce/provider/symmetric/Camellia$AlgParamGen.class at Lorg/spongycastle/jcajce/provider/symmetric/Camellia$AlgParamGen;engineGenerateParameters()Ljava/security/AlgorithmParameters;: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.apk.editor_20.apk --> d8: Error in tmp/monitored_com.apk.editor_20.apk.jar:t2/a.class at Lt2/a;d([B)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.app.missednotificationsreminder_2010605222.apk --> d8: Error in tmp/monitored_com.app.missednotificationsreminder_2010605222.apk.jar:okio/Buffer.class at Lokio/Buffer;hmac(Ljava/lang/String;Lokio/ByteString;)Lokio/ByteString;: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.aravi.dot_30009.apk --> aspectj: MultiSpec_1MonitorAspect.aj [error] Internal compiler error: java.lang.StackOverflowError at org.aspectj.weaver.UnresolvedType.signatureToName(UnresolvedType.java:636)
#APK=$BASE_DIR/com.arduia.expense_11.apk --> dex2jar: java.lang.StringIndexOutOfBoundsException: String index out of range: -2
#APK=$BASE_DIR/com.beemdevelopment.aegis_50.apk --> d8: [CIRCULAR REFERENCE: com.android.tools.r8.internal.Ec: Merging dex file containing classes with prefix 'j$.' with classes with any other prefixes is not allowed: a.A0, a.A, a.B0, a.B, a.C0, a.C, a.D0, a.D, a.E0, a.E, a.F0, a.F...]
##### APK=$BASE_DIR/com.blogspot.e_kanivets.moneytracker_36.apk
#APK=$BASE_DIR/com.brentpanther.bitcoincashwidget_23.apk --> d8: Error in tmp/monitored_com.brentpanther.bitcoincashwidget_23.apk.jar:okio/HashingSource.class at Lokio/HashingSource;<init>(Lokio/Source;Lokio/ByteString;Ljava/lang/String;)V: java.lang.ArrayIndexOutOfBoundsException: -1
### APK=$BASE_DIR/com.brentpanther.bitcoinwidget_287.apk --> aspectj: Type 'kotlin.jvm.functions.Function3' (no debug info available) [error] Mismatch when building parameterization map.
#APK=$BASE_DIR/com.brentpanther.ethereumwidget_33.apk --> d8: Error in tmp/monitored_com.brentpanther.ethereumwidget_33.apk.jar:okio/HashingSource.class at Lokio/HashingSource;<init>(Lokio/Source;Lokio/ByteString;Ljava/lang/String;)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.brentpanther.litecoinwidget_23.apk --> d8: Error in tmp/monitored_com.brentpanther.litecoinwidget_23.apk.jar:okio/HashingSource.class at Lokio/HashingSource;<init>(Lokio/Source;Lokio/ByteString;Ljava/lang/String;)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.btcontract.wallet_86.apk --> d8: Error in tmp/monitored_com.btcontract.wallet_86.apk.jar:okio/Buffer.class at Lokio/Buffer;hmac(Ljava/lang/String;Lokio/ByteString;)Lokio/ByteString;: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.buzbuz.smartautoclicker_11.apk 
##### APK=$BASE_DIR/com.coboltforge.dontmind.multivnc_87.apk
#APK=$BASE_DIR/com.cohenchris.weeklybudget_6.apk
##### APK=$BASE_DIR/com.coinerella.peercoin_60.apk
### APK=$BASE_DIR/com.cosmos.candle_6.apk --> aspectj, but generate apk
### APK=$BASE_DIR/com.crazylegend.vigilante_17.apk --> aspectj and d8, but generate apk
#APK=$BASE_DIR/com.daemon.ssh_12.apk --> aspectj and d8
##### APK=$BASE_DIR/com.decred.decredaddressscanner_10.apk
### APK=$BASE_DIR/com.denytheflowerpot.scrunch_2.apk --> d8 warnings
##### APK=$BASE_DIR/com.dosse.airpods_18.apk
##### APK=$BASE_DIR/com.dosse.dozeoff_2.apk
#APK=$BASE_DIR/com.dx.anonymousmessenger_46.apk --> d8: Error in tmp/monitored_com.dx.anonymousmessenger_46.apk.jar:com/dx/anonymousmessenger/file/FileHelper.class at Lcom/dx/anonymousmessenger/file/FileHelper;decrypt([B[B)[B: java.lang.ArrayIndexOutOfBoundsException: -1
##### APK=$BASE_DIR/com.ebaschiera.triplecamel_14.apk
#APK=$BASE_DIR/com.ecuamobi.deckwallet_100.apk --> d8: Error in tmp/monitored_com.ecuamobi.deckwallet_100.apk.jar:org/spongycastle/crypto/examples/DESExample.class at Lorg/spongycastle/crypto/examples/DESExample;<init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Z)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/com.eletac.tronwallet_37.apk --> d8: Error in tmp/monitored_com.eletac.tronwallet_37.apk.jar:org/spongycastle/jcajce/provider/symmetric/Camellia$AlgParamGen.class at Lorg/spongycastle/jcajce/provider/symmetric/Camellia$AlgParamGen;engineGenerateParameters()Ljava/security/AlgorithmParameters;: java.lang.ArrayIndexOutOfBoundsException: -1
##### APK=$BASE_DIR/com.emanuelef.remote_capture_42.apk
APK=$BASE_DIR/com.marv42.ebt.newnote_5300.apk
#APK=$BASE_DIR/de.php_tech.piggybudget_25.apk --> d8: Error in tmp/monitored_de.php_tech.piggybudget_25.apk.jar:okio/Buffer.class at Lokio/Buffer;hmac(Ljava/lang/String;Lokio/ByteString;)Lokio/ByteString;: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/opencontacts.open.com.opencontacts_24.apk --> d8: Error in tmp/monitored_opencontacts.open.com.opencontacts_24.apk.jar:opencontacts/open/com/opencontacts/utils/NetworkUtils.class at Lopencontacts/open/com/opencontacts/utils/NetworkUtils;getUnsafeOkHttpClientBuilder()Lg4/b0$a;: java.lang.ArrayIndexOutOfBoundsException: -1
##### APK=$BASE_DIR/org.ebur.debitum_14.apk
##### APK=$BASE_DIR/protect.gift_card_guard_6.apk
##### APK=$BASE_DIR/protect.rentalcalc_6.apk
#APK=$BASE_DIR/ru.valle.btc_260.apk --> d8: Error in tmp/monitored_ru.valle.btc_260.apk.jar:org/spongycastle/crypto/examples/DESExample.class at Lorg/spongycastle/crypto/examples/DESExample;<init>(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Z)V: java.lang.ArrayIndexOutOfBoundsException: -1
#APK=$BASE_DIR/threads.server_272.apk --> aspectj


rm out/*

./instrument.sh $APK mop mop-out
 