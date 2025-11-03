
# Tamale Town U.S.A. — Desktop (C2 Build, Backblaze-ready)

This package includes:
- **All stages 0–10** (A0 → C2+) seeders
- **Backblaze B2 (S3) loader** (optional)
- **Express API + Vite/React app + Electron shell**
- **Auto-Accent typing & meaning-first grading** (naive dev version)

## Dev Run
Terminal 1 (API):
```bash
cd server
npm install
cp ../.env.example ../.env  # fill B2 creds if using Backblaze
npm run dev
```
Terminal 2 (Web):
```bash
cd ../app
npm install
npm run dev
```
Terminal 3 (Desktop window):
```bash
cd ../electron
npm install
npm start
```

## Build
- Web: `cd app && npm run build`
- Electron: `cd electron && npm run build` (placeholder; add electron-builder later)

## Backblaze B2
1) Create public bucket (e.g. `tamale-town-seeders`), upload the contents of `/data/seeders` under prefix `seeders/`.
2) Set `.env` (see `.env.example`).  
3) Set `SEEDER_SOURCE=b2` to fetch from B2; otherwise local files are used.
