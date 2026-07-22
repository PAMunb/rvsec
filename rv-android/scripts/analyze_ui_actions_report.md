# Part 1: Action Distribution (Total)

**Total actions across all traces: 290128**

## Action Type Distribution

| Action Type | Count | % |
|-------------|------:|--:|
| BACK | 95878 | 33.0% |
| CLICK | 88941 | 30.7% |
| SKIP | 41280 | 14.2% |
| RESTART | 40812 | 14.1% |
| LONG_CLICK | 11458 | 3.9% |
| SET_TEXT | 10225 | 3.5% |
| SCROLL | 1518 | 0.5% |
| ERROR | 16 | 0.0% |

## Action Source Distribution

| Action Source | Count | % |
|--------------|------:|--:|
| algorithm | 214516 | 73.9% |
| ooa | 34316 | 11.8% |
| ooa_within_tolerance | 20234 | 7.0% |
| null_root | 10693 | 3.7% |
| system_dialog | 8543 | 2.9% |
| native_crash | 1810 | 0.6% |
| exception | 16 | 0.0% |

## Productive vs Wasted

| Category | Count | % |
|----------|------:|--:|
| Productive (algorithm CLICK/LONG_CLICK/SCROLL/SET_TEXT) | 112142 | 38.7% |
| Wasted (SKIP/RESTART from any source) | 82092 | 28.3% |
| Other | 95894 | 33.1% |
| **Productive/Wasted ratio** | **1.37** | |

# Part 2: Per-Activity Action Distribution

## org.asdtm.fas_3.apk (unique_states=154)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| activityMovieDetailsActivity | 399 | 15.9% | CLICK | 18 |
| activityTvDetailsActivity | 394 | 15.7% | CLICK | 19 |
| activityTvActivity | 355 | 14.2% | CLICK | 27 |
| activityHomeActivity | 340 | 13.6% | CLICK | 28 |
| activityMoviesActivity | 274 | 10.9% | CLICK | 23 |
| (empty) | 156 | 6.2% | SKIP | 0 |
| activityVideosActivity | 152 | 6.1% | CLICK | 10 |
| activityVideoActivity | 113 | 4.5% | CLICK | 34 |
| activitySearchActivity | 79 | 3.2% | CLICK | 14 |
| activityDiscoverActivity | 75 | 3.0% | CLICK | 9 |
| activitySettingsActivity | 65 | 2.6% | CLICK | 6 |
| NexusLauncherActivity | 53 | 2.1% | BACK | 11 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 23 | 0.9% | CLICK | 9 |
| comandroidinternalappChooserActivity | 13 | 0.5% | CLICK | 5 |
| activityAboutActivity | 10 | 0.4% | CLICK | 2 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 6 | 0.2% | CLICK | 3 |

## de.koelle.christian.trickytripper_25.apk (unique_states=129)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| TrickyTripperActivity | 694 | 25.7% | CLICK | 41 |
| activitiesParticipantEditActivity | 692 | 25.6% | CLICK | 19 |
| activitiesPaymentEditActivity | 425 | 15.7% | CLICK | 24 |
| (empty) | 262 | 9.7% | RESTART | 0 |
| NexusLauncherActivity | 201 | 7.4% | BACK | 8 |
| activitiesPreferencesActivity | 78 | 2.9% | CLICK | 5 |
| activitiesExchangeRateManageActivity | 76 | 2.8% | CLICK | 9 |
| activitiesExchangeRateEditActivity | 75 | 2.8% | CLICK | 9 |
| activitiesTripEditActivity | 53 | 2.0% | CLICK | 11 |
| activitiesCurrencyCalculatorActivity | 50 | 1.8% | CLICK | 14 |
| activitiesExchangeRateImportActivity | 38 | 1.4% | CLICK | 8 |
| activitiesCurrencySelectionActivity | 32 | 1.2% | CLICK | 9 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 11 | 0.4% | CLICK | 3 |
| activitiesExportActivity | 6 | 0.2% | CLICK | 4 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 6 | 0.2% | BACK | 2 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 2 | 0.1% | CLICK | 1 |
| comandroidinternalappChooserActivity | 2 | 0.1% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 1 | 0.0% | CLICK | 1 |

## com.cyanogenmod.filemanager.ics_1015.apk (unique_states=119)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| activitiesNavigationActivity | 1535 | 80.6% | CLICK | 108 |
| activitiesHistoryActivity | 163 | 8.6% | CLICK | 39 |
| activitiesBookmarksActivity | 120 | 6.3% | CLICK | 37 |
| (empty) | 44 | 2.3% | SKIP | 0 |
| activitiespreferencesSettingsPreferences | 22 | 1.2% | CLICK | 6 |
| comgoogleandroidvoicesearchintentapiIntentApiActivity | 14 | 0.7% | CLICK | 3 |
| activitiesChangeLogActivity | 6 | 0.3% | CLICK | 2 |

## jp.co.kayo.android.localplayer_2071400330.apk (unique_states=101)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| EqualizerActivity | 2337 | 64.4% | CLICK | 41 |
| MainActivity2 | 1151 | 31.7% | CLICK | 104 |
| (empty) | 40 | 1.1% | SKIP | 0 |
| pluginsleeptimerMainActivity | 30 | 0.8% | SET_TEXT | 2 |
| ConfigActivity | 28 | 0.8% | CLICK | 10 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 17 | 0.5% | CLICK | 1 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 16 | 0.4% | CLICK | 3 |
| prefCacheConfigPreference | 5 | 0.1% | CLICK | 3 |
| prefPremiumConfigPreference | 4 | 0.1% | CLICK | 2 |

## net.sourceforge.subsonic.androidapp_59.apk (unique_states=89)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| (empty) | 783 | 27.5% | SKIP | 0 |
| activitySettingsActivity | 565 | 19.9% | CLICK | 11 |
| activityMainActivity | 355 | 12.5% | CLICK | 23 |
| NexusLauncherActivity | 300 | 10.5% | BACK | 5 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 188 | 6.6% | BACK | 5 |
| activityDownloadActivity | 158 | 5.6% | CLICK | 27 |
| activityEqualizerActivity | 108 | 3.8% | CLICK | 6 |
| activitySelectArtistActivity | 102 | 3.6% | CLICK | 18 |
| activitySelectAlbumActivity | 95 | 3.3% | CLICK | 11 |
| launchoobeWhatsNewFullScreen | 84 | 3.0% | BACK | 2 |
| activitySelectPlaylistActivity | 64 | 2.3% | CLICK | 14 |
| activitySearchActivity | 22 | 0.8% | CLICK | 6 |
| activityHelpActivity | 11 | 0.4% | CLICK | 6 |
| comgoogleandroidvoicesearchintentapiIntentApiActivity | 7 | 0.2% | CLICK | 1 |
| comandroidcalendareventLaunchInfoActivity | 2 | 0.1% | CLICK | 1 |

## ohm.quickdice_48.apk (unique_states=69)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| activityQuickDiceMainActivity | 1336 | 61.5% | CLICK | 54 |
| (empty) | 322 | 14.8% | SKIP | 0 |
| activityIconPickerActivity | 184 | 8.5% | LONG_CLICK | 5 |
| activityEditDiceActivity | 151 | 7.0% | CLICK | 10 |
| activityPrefDiceActivity | 56 | 2.6% | CLICK | 6 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 36 | 1.7% | BACK | 6 |
| comandroidinternalappChooserActivity | 28 | 1.3% | CLICK | 5 |
| activityEditBagActivity | 15 | 0.7% | CLICK | 3 |
| pickerPickActivity | 15 | 0.7% | CLICK | 8 |
| activityImportExportActivity | 11 | 0.5% | CLICK | 1 |
| NexusLauncherActivity | 9 | 0.4% | BACK | 2 |
| activityEditVariableActivity | 4 | 0.2% | CLICK | 2 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 3 | 0.1% | CLICK | 3 |
| chooserChooserActivity | 1 | 0.0% | CLICK | 1 |

## com.andybotting.tramhunter_1300.apk (unique_states=60)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| activityFavouriteActivity | 6120 | 77.1% | BACK | 12 |
| (empty) | 517 | 6.5% | RESTART | 0 |
| activityHomeActivity | 314 | 4.0% | CLICK | 20 |
| NexusLauncherActivity | 254 | 3.2% | BACK | 3 |
| activityStopsListActivity | 192 | 2.4% | CLICK | 9 |
| activityRoutesListActivity | 169 | 2.1% | CLICK | 5 |
| activityStopDetailsActivity | 167 | 2.1% | CLICK | 10 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 94 | 1.2% | BACK | 4 |
| activitySettingsActivity | 47 | 0.6% | CLICK | 4 |
| activityNearStopsActivity | 34 | 0.4% | CLICK | 8 |
| activityNetworkMapActivity | 23 | 0.3% | CLICK | 4 |
| activityStopMapActivity | 2 | 0.0% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 1 | 0.0% | CLICK | 1 |

## com.tobykurien.webapps_40.apk (unique_states=60)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| (empty) | 743 | 35.7% | RESTART | 0 |
| NexusLauncherActivity | 280 | 13.4% | CLICK | 8 |
| activityMainActivity | 274 | 13.2% | CLICK | 30 |
| activityWebAppActivity | 254 | 12.2% | CLICK | 51 |
| activityPreferences | 249 | 12.0% | CLICK | 5 |
| comandroidlauncher3settingsSettingsActivity | 118 | 5.7% | CLICK | 3 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 94 | 4.5% | CLICK | 4 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 27 | 1.3% | CLICK | 6 |
| launchoobeWhatsNewFullScreen | 15 | 0.7% | CLICK | 3 |
| Settings$ConfigureNotificationSettingsActivity | 10 | 0.5% | CLICK | 3 |
| comandroidlauncher3dragndropAddItemActivity | 5 | 0.2% | CLICK | 3 |
| comgoogleandroidappsgsavelvetuisettingsSettingsActivity | 4 | 0.2% | LONG_CLICK | 1 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 3 | 0.1% | LONG_CLICK | 3 |
| comandroidcalendareventLaunchInfoActivity | 2 | 0.1% | CLICK | 2 |
| comandroidinternalappChooserActivity | 2 | 0.1% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 1 | 0.0% | CLICK | 1 |
| comgoogleandroidappsgsavelvetuisettingsPublicSettingsActivity | 1 | 0.0% | CLICK | 1 |

## com.crazyhitty.chdev.ks.munch_14.apk (unique_states=58)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| (empty) | 1276 | 45.0% | SKIP | 0 |
| uiactivitiesHomeActivity | 849 | 29.9% | CLICK | 33 |
| NexusLauncherActivity | 303 | 10.7% | BACK | 10 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 240 | 8.5% | BACK | 9 |
| uiactivitiesArticleActivity | 99 | 3.5% | CLICK | 7 |
| uiactivitiesSettingsActivity | 24 | 0.8% | CLICK | 6 |
| uiactivitiesAboutActivity | 15 | 0.5% | CLICK | 6 |
| uiactivitiesSplashActivity | 12 | 0.4% | SCROLL | 1 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 6 | 0.2% | CLICK | 4 |
| comandroidinternalappResolverActivity | 5 | 0.2% | CLICK | 3 |
| launchoobeWhatsNewFullScreen | 3 | 0.1% | BACK | 2 |
| comgoogleandroidappsgsasidekickmainoptinOptInActivity | 2 | 0.1% | BACK | 2 |
| comandroidcalendareventLaunchInfoActivity | 1 | 0.0% | CLICK | 1 |
| comgoogleandroidappsgsasharedutilpermissionsProxyActivity | 1 | 0.0% | SCROLL | 1 |

## io.github.tjg1.nori_15.apk (unique_states=58)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| APISettingsActivity | 2485 | 69.9% | BACK | 10 |
| (empty) | 365 | 10.3% | SKIP | 0 |
| SearchActivity | 362 | 10.2% | BACK | 24 |
| ImageViewerActivity | 233 | 6.6% | CLICK | 12 |
| SettingsActivity | 47 | 1.3% | CLICK | 7 |
| NexusLauncherActivity | 16 | 0.5% | BACK | 3 |
| TagFilterSettingsActivity | 15 | 0.4% | CLICK | 3 |
| SafeSearchSettingsActivity | 12 | 0.3% | CLICK | 2 |
| shareitemUploadMenuActivity | 4 | 0.1% | CLICK | 3 |
| DonationActivity | 4 | 0.1% | CLICK | 2 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 3 | 0.1% | CLICK | 2 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 2 | 0.1% | CLICK | 2 |
| oppBluetoothOppLauncherActivity | 2 | 0.1% | CLICK | 2 |
| oppBluetoothOppBtEnableActivity | 2 | 0.1% | CLICK | 2 |
| driveclipboardSendTextToClipboardActivity | 2 | 0.1% | CLICK | 2 |

## io.gresse.hugo.anecdote_23.apk (unique_states=54)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| MainActivity | 1043 | 45.8% | CLICK | 38 |
| (empty) | 758 | 33.3% | SKIP | 0 |
| NexusLauncherActivity | 247 | 10.8% | BACK | 8 |
| launchoobeWhatsNewFullScreen | 121 | 5.3% | BACK | 2 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 76 | 3.3% | BACK | 5 |
| comandroidinternalappChooserActivity | 16 | 0.7% | CLICK | 8 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 10 | 0.4% | CLICK | 3 |
| welcomeWelcomeTourActivity | 2 | 0.1% | LONG_CLICK | 1 |
| ComposeActivityGmailExternal | 2 | 0.1% | CLICK | 2 |
| comandroidcalendareventLaunchInfoActivity | 1 | 0.0% | CLICK | 1 |
| chooserChooserActivity | 1 | 0.0% | CLICK | 1 |

## eu.bubu1.fdroidclassic_1110.apk (unique_states=51)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| orgfdroidfdroidFDroid | 1561 | 56.0% | CLICK | 32 |
| (empty) | 695 | 24.9% | SKIP | 0 |
| welcomeWelcomeTourActivity | 156 | 5.6% | CLICK | 5 |
| launchoobeWhatsNewFullScreen | 127 | 4.6% | CLICK | 3 |
| orgfdroidfdroidPreferencesActivity | 104 | 3.7% | CLICK | 7 |
| orgfdroidfdroidviewsManageReposActivity | 42 | 1.5% | CLICK | 7 |
| NexusLauncherActivity | 41 | 1.5% | CLICK | 5 |
| orgfdroidfdroidviewsRepoDetailsActivity | 32 | 1.1% | CLICK | 6 |
| comandroidinternalappChooserActivity | 14 | 0.5% | CLICK | 3 |
| orgfdroidfdroidAboutActivity | 9 | 0.3% | CLICK | 2 |
| ComposeActivityGmailExternal | 3 | 0.1% | CLICK | 1 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 2 | 0.1% | LONG_CLICK | 1 |

## org.pulpdust.lesserpad_42.apk (unique_states=50)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| LesserPadActivity | 473 | 20.7% | CLICK | 21 |
| (empty) | 453 | 19.8% | RESTART | 0 |
| LesserPadPrefs | 403 | 17.6% | CLICK | 18 |
| NexusLauncherActivity | 340 | 14.8% | BACK | 8 |
| LesserPadListActivity | 298 | 13.0% | CLICK | 18 |
| CategoryEditor | 250 | 10.9% | CLICK | 15 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 56 | 2.4% | BACK | 2 |
| comandroidinternalappResolverActivity | 13 | 0.6% | CLICK | 4 |
| ProtectActivity | 3 | 0.1% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 1 | 0.0% | CLICK | 1 |

## com.alienpants.leafpicrevived_24.apk (unique_states=47)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| (empty) | 825 | 41.2% | RESTART | 0 |
| NexusLauncherActivity | 651 | 32.5% | BACK | 7 |
| activitiesMainActivity | 322 | 16.1% | CLICK | 22 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 117 | 5.8% | BACK | 5 |
| activitiesSettingsActivity | 63 | 3.1% | CLICK | 11 |
| activitiesBlackWhiteListActivity | 12 | 0.6% | CLICK | 9 |
| aboutAboutActivity | 6 | 0.3% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 2 | 0.1% | CLICK | 1 |
| activitiesSecurityActivity | 2 | 0.1% | CLICK | 2 |

## com.quaap.launchtime_850.apk (unique_states=47)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| MainActivity | 397 | 46.7% | CLICK | 33 |
| (empty) | 203 | 23.9% | SKIP | 0 |
| ColorSettingsActivity | 139 | 16.3% | CLICK | 7 |
| uitutorialTutorialSelectAccountActivity | 15 | 1.8% | CLICK | 4 |
| SettingsActivity | 14 | 1.6% | CLICK | 6 |
| AboutActivity | 14 | 1.6% | SCROLL | 2 |
| mainimplMainActivity | 12 | 1.4% | CLICK | 3 |
| uiconversationlistConversationListActivity | 11 | 1.3% | CLICK | 3 |
| welcomeWelcomeTourActivity | 9 | 1.1% | CLICK | 3 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 8 | 0.9% | CLICK | 2 |
| orgchromiumchromebrowserChromeTabbedActivity | 4 | 0.5% | CLICK | 1 |
| uiHomeActivity | 4 | 0.5% | CLICK | 1 |
| comandroidpackageinstallerpermissionuiGrantPermissionsActivity | 4 | 0.5% | LONG_CLICK | 2 |
| uiMailActivityGmail | 3 | 0.4% | CLICK | 1 |
| comandroidcameraCameraActivity | 3 | 0.4% | CLICK | 1 |
| activitiesPeopleActivity | 3 | 0.4% | CLICK | 2 |
| comandroidcalendareventLaunchInfoActivity | 2 | 0.2% | CLICK | 2 |
| homepageSettingsHomepageActivity | 2 | 0.2% | CLICK | 2 |
| comandroidwallpaperpickerTopLevelPickerActivity | 2 | 0.2% | CLICK | 2 |
| launchoobeWhatsNewFullScreen | 1 | 0.1% | LONG_CLICK | 1 |
| comandroidcameraPermissionsActivity | 1 | 0.1% | CLICK | 1 |

## t20kdc.offlinepuzzlesolver_4.apk (unique_states=46)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| (empty) | 634 | 32.0% | RESTART | 0 |
| NexusLauncherActivity | 491 | 24.8% | BACK | 9 |
| gameNCupsActivity | 222 | 11.2% | CLICK | 8 |
| SolutionActivity | 172 | 8.7% | CLICK | 10 |
| gameSudokuActivity | 118 | 6.0% | CLICK | 9 |
| orgchromiumchromebrowserfirstrunFirstRunActivity | 105 | 5.3% | CLICK | 8 |
| ungameNetGuardChallengeActivity | 94 | 4.7% | SET_TEXT | 2 |
| MainActivity | 78 | 3.9% | BACK | 10 |
| WorkingActivity | 29 | 1.5% | CLICK | 8 |
| CreditsActivity | 25 | 1.3% | CLICK | 4 |
| gameNQueensActivity | 12 | 0.6% | CLICK | 2 |
| orgchromiumchromebrowserdocumentChromeLauncherActivity | 1 | 0.1% | CLICK | 1 |

## com.github.axet.binauralbeats_160.apk (unique_states=45)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| activitiesMainActivity | 2277 | 88.6% | CLICK | 47 |
| (empty) | 158 | 6.1% | SKIP | 0 |
| NexusLauncherActivity | 91 | 3.5% | BACK | 11 |
| activitiesSettingsActivity | 34 | 1.3% | CLICK | 3 |
| Settings$ZenAccessSettingsActivity | 10 | 0.4% | CLICK | 2 |
| pickerPickActivity | 1 | 0.0% | CLICK | 1 |

## com.zzzmode.appopsx_125.apk (unique_states=45)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| uimainMainActivity | 1627 | 48.5% | CLICK | 21 |
| (empty) | 755 | 22.5% | RESTART | 0 |
| NexusLauncherActivity | 425 | 12.7% | BACK | 10 |
| uimainSettingsActivity | 206 | 6.1% | CLICK | 9 |
| launchoobeWhatsNewFullScreen | 109 | 3.2% | BACK | 3 |
| uipermissionAppPermissionActivity | 96 | 2.9% | CLICK | 6 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 79 | 2.4% | BACK | 4 |
| uimainbackupBackupActivity | 38 | 1.1% | CLICK | 4 |
| uimainusagestatsPermsUsageStatsActivity | 11 | 0.3% | CLICK | 2 |
| uimaingroupPermissionGroupActivity | 8 | 0.2% | CLICK | 3 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 1 | 0.0% | CLICK | 1 |

## de.kaffeemitkoffein.imagepipe_45.apk (unique_states=43)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| ImageReceiver | 1462 | 69.2% | LONG_CLICK | 21 |
| (empty) | 472 | 22.3% | SKIP | 0 |
| pickerexternalExternalPickerActivity | 54 | 2.6% | CLICK | 12 |
| comandroidinternalappChooserActivity | 44 | 2.1% | CLICK | 11 |
| Settings | 34 | 1.6% | CLICK | 4 |
| NexusLauncherActivity | 21 | 1.0% | LONG_CLICK | 4 |
| chooserChooserActivity | 12 | 0.6% | CLICK | 8 |
| comandroidpackageinstallerpermissionuiGrantPermissionsActivity | 6 | 0.3% | SET_TEXT | 1 |
| ImagePipeInfo | 5 | 0.2% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginsopaOpaActivity | 1 | 0.0% | LONG_CLICK | 1 |
| comgoogleandroidappsgsavelourdynamichostsTransparentVelvetDynamicHostActivity | 1 | 0.0% | LONG_CLICK | 1 |

## com.blogspot.e_kanivets.moneytracker_38.apk (unique_states=40)

| Activity | Visits | % of total | Dominant action | Unique hashes |
|----------|-------:|-----------:|-----------------|---------------:|
| NexusLauncherActivity | 459 | 26.8% | BACK | 5 |
| activityrecordAddRecordActivity | 458 | 26.7% | CLICK | 12 |
| (empty) | 387 | 22.6% | RESTART | 0 |
| activityrecordMainActivity | 250 | 14.6% | CLICK | 15 |
| activityReportActivity | 114 | 6.7% | CLICK | 4 |
| activityaccountAccountsActivity | 20 | 1.2% | CLICK | 7 |
| activityaccounteditEditAccountActivity | 9 | 0.5% | CLICK | 3 |
| comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 6 | 0.4% | CLICK | 3 |
| activityaccountTransferActivity | 5 | 0.3% | CLICK | 3 |
| activityexchange_rateExchangeRatesActivity | 2 | 0.1% | CLICK | 2 |
| comgoogleandroidappsgsastaticpluginssmartspaceExportedSmartspaceTrampolineActivity | 2 | 0.1% | CLICK | 1 |
| activityaccountAddAccountActivity | 2 | 0.1% | CLICK | 2 |

## Activities with dominant BACK or RESTART (potential stuck)

| APK | Activity | Visits | Dominant action |
|-----|----------|-------:|-----------------|
| org.asdtm.fas_3.apk | NexusLauncherActivity | 53 | BACK |
| de.koelle.christian.trickytripper_25.apk | (empty) | 262 | RESTART |
| de.koelle.christian.trickytripper_25.apk | NexusLauncherActivity | 201 | BACK |
| de.koelle.christian.trickytripper_25.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 6 | BACK |
| net.sourceforge.subsonic.androidapp_59.apk | NexusLauncherActivity | 300 | BACK |
| net.sourceforge.subsonic.androidapp_59.apk | launchoobeWhatsNewFullScreen | 84 | BACK |
| net.sourceforge.subsonic.androidapp_59.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 188 | BACK |
| ohm.quickdice_48.apk | orgchromiumchromebrowserfirstrunFirstRunActivity | 36 | BACK |
| ohm.quickdice_48.apk | NexusLauncherActivity | 9 | BACK |
| com.andybotting.tramhunter_1300.apk | (empty) | 517 | RESTART |
| com.andybotting.tramhunter_1300.apk | activityFavouriteActivity | 6120 | BACK |
| com.andybotting.tramhunter_1300.apk | NexusLauncherActivity | 254 | BACK |
| com.andybotting.tramhunter_1300.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 94 | BACK |
| com.tobykurien.webapps_40.apk | (empty) | 743 | RESTART |
| com.crazyhitty.chdev.ks.munch_14.apk | NexusLauncherActivity | 303 | BACK |
| com.crazyhitty.chdev.ks.munch_14.apk | orgchromiumchromebrowserfirstrunFirstRunActivity | 240 | BACK |
| io.github.tjg1.nori_15.apk | SearchActivity | 362 | BACK |
| io.github.tjg1.nori_15.apk | APISettingsActivity | 2485 | BACK |
| io.github.tjg1.nori_15.apk | NexusLauncherActivity | 16 | BACK |
| io.gresse.hugo.anecdote_23.apk | NexusLauncherActivity | 247 | BACK |
| io.gresse.hugo.anecdote_23.apk | launchoobeWhatsNewFullScreen | 121 | BACK |
| io.gresse.hugo.anecdote_23.apk | orgchromiumchromebrowserfirstrunFirstRunActivity | 76 | BACK |
| org.pulpdust.lesserpad_42.apk | (empty) | 453 | RESTART |
| org.pulpdust.lesserpad_42.apk | NexusLauncherActivity | 340 | BACK |
| org.pulpdust.lesserpad_42.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 56 | BACK |
| com.alienpants.leafpicrevived_24.apk | NexusLauncherActivity | 651 | BACK |
| com.alienpants.leafpicrevived_24.apk | (empty) | 825 | RESTART |
| com.alienpants.leafpicrevived_24.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 117 | BACK |
| t20kdc.offlinepuzzlesolver_4.apk | MainActivity | 78 | BACK |
| t20kdc.offlinepuzzlesolver_4.apk | (empty) | 634 | RESTART |
| t20kdc.offlinepuzzlesolver_4.apk | NexusLauncherActivity | 491 | BACK |
| com.github.axet.binauralbeats_160.apk | NexusLauncherActivity | 91 | BACK |
| com.zzzmode.appopsx_125.apk | NexusLauncherActivity | 425 | BACK |
| com.zzzmode.appopsx_125.apk | (empty) | 755 | RESTART |
| com.zzzmode.appopsx_125.apk | launchoobeWhatsNewFullScreen | 109 | BACK |
| com.zzzmode.appopsx_125.apk | comgoogleandroidappsgsavelourdynamichostsVelvetDynamicHostActivity | 79 | BACK |
| com.blogspot.e_kanivets.moneytracker_38.apk | NexusLauncherActivity | 459 | BACK |
| com.blogspot.e_kanivets.moneytracker_38.apk | (empty) | 387 | RESTART |

# Part 3: Per-Screen (hash) Analysis

## org.asdtm.fas_3.apk (unique_states=154)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| 01e771a0 | 179 | activityHomeActivity | CLICK | 0.80 |
| 46624ce0 | 171 | activityTvActivity | CLICK | 0.00 |
| (empty) | 156 |  | SKIP | N/A |
| dd41197b | 120 | activityMoviesActivity | CLICK | 0.00 |
| 1dda6b18 | 120 | activityTvDetailsActivity | CLICK | 0.60 |

**One-shot screens (visited once):** 64

**Screens with >20 visits (potential stuck loops):** 29

| Hash | Visits |
|------|-------:|
| 01e771a0 | 179 |
| 46624ce0 | 171 |
| dd41197b | 120 |
| 1dda6b18 | 120 |
| b2976211 | 92 |
| e2e3e06f | 81 |
| d13671e8 | 69 |
| 9115738c | 57 |
| cbffbbde | 49 |
| 6a1fd273 | 44 |
| dddbaeca | 40 |
| e2bd2a00 | 38 |
| d164301b | 34 |
| eece1cba | 34 |
| a5036e13 | 34 |
| 43c48e79 | 34 |
| 9f028df4 | 32 |
| f6afd3e3 | 30 |
| 67de54f7 | 28 |
| b27d26a3 | 26 |
| 7a69baea | 26 |
| fe382b72 | 26 |
| 93c41137 | 25 |
| a5c177a0 | 24 |
| ff0bcc02 | 24 |
| 93b17f86 | 22 |
| deff8598 | 22 |
| 4d02c2a6 | 21 |
| 35bda8d9 | 21 |

## de.koelle.christian.trickytripper_25.apk (unique_states=129)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| 1ccd1cf8 | 279 | activitiesParticipantEditActivity | CLICK | 0.67 |
| (empty) | 262 |  | RESTART | N/A |
| 9c8c72a9 | 262 | TrickyTripperActivity | BACK | 1.00 |
| 7fb90428 | 162 | activitiesParticipantEditActivity | CLICK | 1.00 |
| d763a823 | 134 | activitiesPaymentEditActivity | CLICK | 0.27 |

**One-shot screens (visited once):** 53

**Screens with >20 visits (potential stuck loops):** 24

| Hash | Visits |
|------|-------:|
| 1ccd1cf8 | 279 |
| 9c8c72a9 | 262 |
| 7fb90428 | 162 |
| d763a823 | 134 |
| a5c177a0 | 109 |
| 2fca2431 | 99 |
| 56e14448 | 97 |
| b71102fc | 80 |
| 5ea5f54a | 69 |
| 8c5d5c62 | 56 |
| e76e08fd | 53 |
| e4027c5b | 47 |
| 11b4fc8b | 46 |
| c8ecd146 | 45 |
| 33fe0096 | 45 |
| 93267ffc | 40 |
| ec0a4549 | 36 |
| 17d85339 | 35 |
| 172401be | 31 |
| ba665d28 | 25 |
| 9627f4ef | 25 |
| 23c231f6 | 25 |
| c8a1c924 | 24 |
| ac8629ac | 22 |

## com.cyanogenmod.filemanager.ics_1015.apk (unique_states=119)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| c6028cd0 | 259 | activitiesNavigationActivity | LONG_CLICK | 0.68 |
| bf14b0fd | 81 | activitiesNavigationActivity | CLICK | 0.92 |
| 8fb841ab | 72 | activitiesNavigationActivity | CLICK | 0.00 |
| da58d014 | 55 | activitiesNavigationActivity | CLICK | 0.00 |
| 80da2edf | 55 | activitiesNavigationActivity | CLICK | 0.00 |

**One-shot screens (visited once):** 73

**Screens with >20 visits (potential stuck loops):** 25

| Hash | Visits |
|------|-------:|
| c6028cd0 | 259 |
| bf14b0fd | 81 |
| 8fb841ab | 72 |
| da58d014 | 55 |
| 80da2edf | 55 |
| 1f510a36 | 50 |
| d85bd4f2 | 47 |
| 022f6ee7 | 43 |
| f8c11ef8 | 41 |
| aad89675 | 36 |
| 445eb5c9 | 35 |
| db4c1661 | 35 |
| cb346677 | 35 |
| 85a52e4a | 35 |
| 7615a260 | 33 |
| 63fb67d0 | 31 |
| 26fe2a3d | 28 |
| dba64d57 | 28 |
| cea00cf4 | 28 |
| 9ba30d5a | 24 |
| d96fc852 | 24 |
| 2aaeb69f | 23 |
| ca4e458e | 21 |
| ed001090 | 21 |
| a81e2eb0 | 21 |

## jp.co.kayo.android.localplayer_2071400330.apk (unique_states=101)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| 58809714 | 1153 | EqualizerActivity | BACK | 0.55 |
| f4cfa40b | 763 | EqualizerActivity | CLICK | 0.89 |
| f4cfa409 | 170 | EqualizerActivity | CLICK | 0.86 |
| ef24bf62 | 100 | MainActivity2 | CLICK | 0.00 |
| d392f459 | 75 | EqualizerActivity | CLICK | 1.00 |

**One-shot screens (visited once):** 53

**Screens with >20 visits (potential stuck loops):** 20

| Hash | Visits |
|------|-------:|
| 58809714 | 1153 |
| f4cfa40b | 763 |
| f4cfa409 | 170 |
| ef24bf62 | 100 |
| d392f459 | 75 |
| 2bf75d22 | 72 |
| 3ca3fd4b | 68 |
| 2f7b2777 | 65 |
| 6dd2dff2 | 63 |
| 19bfab7b | 53 |
| e6043a1d | 45 |
| c6adaba0 | 45 |
| 670e3a2a | 39 |
| 32121a11 | 38 |
| bdcddc55 | 37 |
| b093c692 | 32 |
| 2677940c | 32 |
| 87744926 | 29 |
| b693b88a | 23 |
| 184a012d | 22 |

## net.sourceforge.subsonic.androidapp_59.apk (unique_states=89)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| (empty) | 783 |  | SKIP | N/A |
| 658c0ffe | 191 | NexusLauncherActivity | BACK | 0.00 |
| 5b168f07 | 176 | activityMainActivity | CLICK | 0.87 |
| 2207dbbd | 166 | activitySettingsActivity | CLICK | 1.00 |
| d99b138d | 116 | activitySettingsActivity | CLICK | 1.00 |

**One-shot screens (visited once):** 44

**Screens with >20 visits (potential stuck loops):** 23

| Hash | Visits |
|------|-------:|
| 658c0ffe | 191 |
| 5b168f07 | 176 |
| 2207dbbd | 166 |
| d99b138d | 116 |
| cfd7d9b5 | 110 |
| a5c177a0 | 106 |
| dcd61f5f | 73 |
| f71be931 | 70 |
| 01465c06 | 54 |
| 8d57a292 | 53 |
| b8395ad2 | 46 |
| 594e9998 | 39 |
| b325ee33 | 39 |
| c0e7482f | 38 |
| f0b4fc96 | 37 |
| e74e2fdf | 31 |
| 0f41ea6a | 31 |
| 67313ba3 | 30 |
| dda174e3 | 27 |
| 94d3075b | 25 |
| 2c142875 | 25 |
| 6dba9c12 | 22 |
| c2ff82ed | 21 |

## ohm.quickdice_48.apk (unique_states=69)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| (empty) | 322 |  | SKIP | N/A |
| a66efe8a | 279 | activityQuickDiceMainActivity | LONG_CLICK | 0.89 |
| 18420953 | 124 | activityQuickDiceMainActivity | CLICK | 0.00 |
| f3bfe066 | 117 | activityQuickDiceMainActivity | BACK | 0.81 |
| f441ee49 | 91 | activityEditDiceActivity | SET_TEXT | 0.00 |

**One-shot screens (visited once):** 29

**Screens with >20 visits (potential stuck loops):** 22

| Hash | Visits |
|------|-------:|
| a66efe8a | 279 |
| 18420953 | 124 |
| f3bfe066 | 117 |
| f441ee49 | 91 |
| bd4a53a2 | 90 |
| 1742679b | 79 |
| a28e0371 | 71 |
| 71977aed | 70 |
| d4c7678a | 66 |
| 3d2537e5 | 60 |
| 7b9bb7c7 | 59 |
| 2ada41c0 | 50 |
| 75fd6f42 | 39 |
| c3e1948f | 39 |
| a4ef456a | 38 |
| ff99ba3a | 35 |
| 4ae1043d | 35 |
| b2972b1d | 35 |
| a165cd91 | 31 |
| 9d60befd | 29 |
| 31ee3b20 | 27 |
| d85f164c | 22 |

## com.andybotting.tramhunter_1300.apk (unique_states=60)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| 51141768 | 6038 | activityFavouriteActivity | BACK | 0.00 |
| (empty) | 517 |  | RESTART | N/A |
| 105f2864 | 154 | activityHomeActivity | CLICK | 1.00 |
| f0465933 | 151 | NexusLauncherActivity | BACK | 0.00 |
| a5c177a0 | 102 | NexusLauncherActivity | CLICK | N/A |

**One-shot screens (visited once):** 23

**Screens with >20 visits (potential stuck loops):** 20

| Hash | Visits |
|------|-------:|
| 51141768 | 6038 |
| 105f2864 | 154 |
| f0465933 | 151 |
| a5c177a0 | 102 |
| 830b389a | 97 |
| 31652081 | 88 |
| 65c6ce63 | 63 |
| 3d83ff5c | 60 |
| d1e84dab | 47 |
| 7fbec1d6 | 41 |
| 5556d491 | 37 |
| 0e920d5f | 32 |
| c38a61f0 | 32 |
| db46debb | 30 |
| f71be931 | 30 |
| 0644a4c7 | 28 |
| 1ec66bf4 | 28 |
| 50cbe6a1 | 27 |
| 5f19848a | 26 |
| f367b0a5 | 24 |

## com.tobykurien.webapps_40.apk (unique_states=60)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| (empty) | 743 |  | RESTART | N/A |
| 5facc332 | 208 | NexusLauncherActivity | CLICK | 0.00 |
| e9d4f7cd | 107 | activityPreferences | CLICK | 0.00 |
| 40338989 | 94 | activityMainActivity | CLICK | 0.80 |
| 790ed366 | 81 | comandroidlauncher3settingsSettingsActivity | BACK | 0.50 |

**One-shot screens (visited once):** 58

**Screens with >20 visits (potential stuck loops):** 15

| Hash | Visits |
|------|-------:|
| 5facc332 | 208 |
| e9d4f7cd | 107 |
| 40338989 | 94 |
| 790ed366 | 81 |
| 64106f3a | 73 |
| 2b7a6c8c | 60 |
| 96b76b72 | 58 |
| a5c177a0 | 55 |
| bd087c1b | 55 |
| a2693755 | 44 |
| c8b5e073 | 36 |
| f71be931 | 32 |
| 0ff5e347 | 27 |
| fe661d67 | 21 |
| 8572f9b7 | 21 |

## com.crazyhitty.chdev.ks.munch_14.apk (unique_states=58)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| (empty) | 1276 |  | SKIP | N/A |
| cc578fe4 | 258 | uiactivitiesHomeActivity | CLICK | 1.00 |
| 81cd33ce | 180 | orgchromiumchromebrowserfirstrunFirstRunActivity | BACK | 0.75 |
| f76d9883 | 165 | NexusLauncherActivity | BACK | 0.00 |
| d8ff8577 | 135 | uiactivitiesHomeActivity | SET_TEXT | 0.57 |

**One-shot screens (visited once):** 30

**Screens with >20 visits (potential stuck loops):** 16

| Hash | Visits |
|------|-------:|
| cc578fe4 | 258 |
| 81cd33ce | 180 |
| f76d9883 | 165 |
| d8ff8577 | 135 |
| 4b0fc954 | 114 |
| 0c06ca83 | 84 |
| 14e1f5f2 | 67 |
| 85d79c7e | 60 |
| 4af123c2 | 54 |
| 85abeb9f | 51 |
| a5c177a0 | 40 |
| 66116aa4 | 26 |
| d3ad956e | 23 |
| e541a335 | 22 |
| 50973c37 | 22 |
| ddeac9d0 | 21 |

## io.github.tjg1.nori_15.apk (unique_states=58)

### Top 5 most-visited screens

| Hash | Visits | Activity | Dominant action | Last saturation_rate |
|------|-------:|----------|-----------------|---------------------:|
| e155e3b4 | 1043 | APISettingsActivity | BACK | 1.00 |
| 3b290f11 | 798 | APISettingsActivity | CLICK | 1.00 |
| 50b53f1b | 617 | APISettingsActivity | BACK | 1.00 |
| (empty) | 365 |  | SKIP | N/A |
| 1830db66 | 101 | SearchActivity | BACK | 1.00 |

**One-shot screens (visited once):** 23

**Screens with >20 visits (potential stuck loops):** 13

| Hash | Visits |
|------|-------:|
| e155e3b4 | 1043 |
| 3b290f11 | 798 |
| 50b53f1b | 617 |
| 1830db66 | 101 |
| 2d221268 | 94 |
| a8d58e63 | 52 |
| 1bc2b608 | 49 |
| d69c062e | 40 |
| dff9f7e3 | 39 |
| f334b7c5 | 32 |
| c8f87310 | 29 |
| 7e1fa27b | 28 |
| fe130294 | 22 |

# Part 4: Widget Class Distribution

**Empty widget_class: 177411 (61.1%)** — typically BACK, RESTART, SKIP actions

## Overall widget_class distribution (top 15, excluding empty)

| Widget Class | Count | % |
|-------------|------:|--:|
| Button | 23919 | 8.2% |
| LinearLayout | 20868 | 7.2% |
| TextView | 15852 | 5.5% |
| ImageView | 12292 | 4.2% |
| EditText | 11997 | 4.1% |
| ImageButton | 9544 | 3.3% |
| Spinner | 6224 | 2.1% |
| FrameLayout | 3053 | 1.1% |
| CheckedTextView | 2871 | 1.0% |
| RelativeLayout | 1893 | 0.7% |
| CheckBox | 628 | 0.2% |
| ListView | 602 | 0.2% |
| ActionBar$Tab | 532 | 0.2% |
| ViewPager | 340 | 0.1% |
| WebView | 323 | 0.1% |

## Widget classes for CLICK actions (total=88941)

| Widget Class | Count | % of CLICKs |
|-------------|------:|------------:|
| Button | 23841 | 26.8% |
| LinearLayout | 19834 | 22.3% |
| TextView | 13728 | 15.4% |
| ImageView | 11238 | 12.6% |
| ImageButton | 8465 | 9.5% |
| CheckedTextView | 2870 | 3.2% |
| FrameLayout | 2832 | 3.2% |
| Spinner | 1907 | 2.1% |
| EditText | 972 | 1.1% |
| RelativeLayout | 950 | 1.1% |
| CheckBox | 623 | 0.7% |
| ActionBar$Tab | 526 | 0.6% |
| WebView | 209 | 0.2% |
| LinearLayoutCompat | 194 | 0.2% |
| aq | 151 | 0.2% |

# Part 5: Exploration Efficiency

## Top 10 most efficient APKs (by new_states_per_minute)

| APK | unique_states | total_iters | elapsed_s | states/min | productive_ratio |
|-----|------:|------:|------:|------:|------:|
| org.asdtm.fas_3.apk | 154 | 2507 | 597 | 15.48 | 0.85 |
| de.koelle.christian.trickytripper_25.apk | 129 | 2704 | 596 | 12.99 | 0.71 |
| com.cyanogenmod.filemanager.ics_1015.apk | 119 | 1904 | 596 | 11.97 | 0.92 |
| com.quaap.launchtime_850.apk | 47 | 851 | 275 | 10.26 | 0.69 |
| jp.co.kayo.android.localplayer_2071400330.apk | 101 | 3628 | 597 | 10.16 | 0.75 |
| net.sourceforge.subsonic.androidapp_59.apk | 89 | 2844 | 596 | 8.96 | 0.51 |
| ohm.quickdice_48.apk | 69 | 2171 | 596 | 6.94 | 0.71 |
| com.tobykurien.webapps_40.apk | 60 | 2082 | 596 | 6.04 | 0.54 |
| com.andybotting.tramhunter_1300.apk | 60 | 7934 | 597 | 6.03 | 0.12 |
| com.crazyhitty.chdev.ks.munch_14.apk | 58 | 2836 | 596 | 5.84 | 0.33 |

## Bottom 10 least efficient APKs

| APK | unique_states | total_iters | elapsed_s | states/min | productive_ratio |
|-----|------:|------:|------:|------:|------:|
| com.maxfierke.sandwichroulette_2.apk | 1 | 998 | 596 | 0.10 | 0.00 |
| com.mishiranu.dashchan_1043.apk | 0 | 1577 | 596 | 0.00 | 0.00 |
| com.spisoft.quicknote_241.apk | 0 | 1577 | 597 | 0.00 | 0.00 |
| info.guardianproject.gilga_11.apk | 0 | 819 | 596 | 0.00 | 0.00 |
| info.metadude.android.debconf.schedule_85.apk | 0 | 1505 | 595 | 0.00 | 0.00 |
| io.github.installalogs_10.apk | 0 | 1456 | 596 | 0.00 | 0.00 |
| ohi.andre.consolelauncher_205.apk | 0 | 3552 | 597 | 0.00 | 0.00 |
| org.moire.ultrasonic_129.apk | 0 | 1415 | 596 | 0.00 | 0.00 |
| pw.thedrhax.mosmetro_77.apk | 0 | 1581 | 595 | 0.00 | 0.00 |
| tk.giesecke.painlessmesh_14.apk | 0 | 1507 | 596 | 0.00 | 0.00 |

