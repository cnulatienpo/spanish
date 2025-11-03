# Sign & Ship (iOS / TestFlight)

1. Xcode → Product > Archive.
2. Create App ID in App Store Connect (Bundle ID matches capacitor.config.ts).
3. Certificates & Profiles via Xcode automatic signing.
4. Distribute to TestFlight; add internal testers; wait for review.
5. Prepare App Store listing; submit for review.

Tip: Add one native capability (Push/Share/Files) for "not just a webview" check.
