# Mobile Release Checklist

- [ ] Install Capacitor + platforms
- [ ] Merge scripts from config/package.scripts.json
- [ ] Add `config/capacitor.config.ts` at project root
- [ ] Add PWA bits (manifest, service worker, index snippet)
- [ ] `npm run build` → `npx cap copy`
- [ ] `npx cap add android` / `npx cap add ios`
- [ ] `npx @capacitor/assets generate` (icons & splash)
- [ ] Android signing → upload AAB (Play Console)
- [ ] iOS archive → TestFlight → Release
- [ ] Fill store listings; upload screenshots
- [ ] Link Privacy Policy; complete Data Safety / App Privacy
