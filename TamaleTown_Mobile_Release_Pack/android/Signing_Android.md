# Sign & Upload (Android, Play Console)

1. Create keystore
```bash
keytool -genkey -v -keystore tt-release.keystore -alias tt_key -keyalg RSA -keysize 2048 -validity 10000
```

2. Configure in `android/gradle.properties`
```
TT_STORE_FILE=tt-release.keystore
TT_STORE_PASSWORD=***
TT_KEY_ALIAS=tt_key
TT_KEY_PASSWORD=***
```

3. Reference in `app/build.gradle`
```
signingConfigs {
  release {
    storeFile file(System.getenv("TT_STORE_FILE") ?: TT_STORE_FILE)
    storePassword System.getenv("TT_STORE_PASSWORD") ?: TT_STORE_PASSWORD
    keyAlias System.getenv("TT_KEY_ALIAS") ?: TT_KEY_ALIAS
    keyPassword System.getenv("TT_KEY_PASSWORD") ?: TT_KEY_PASSWORD
  }
}
buildTypes { release { signingConfig signingConfigs.release; minifyEnabled true; shrinkResources true; } }
```

4. Build AAB:
```
./gradlew bundleRelease
```
Upload `app-release.aab` in Play Console → Production.
