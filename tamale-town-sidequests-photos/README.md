
# Tamale Town U.S.A. — Sidequests + Photos Build

This package includes:
- Stages 0–2 (starter) and 7–10 (C1–C2 endgame) seeders
- 12 culture/festival sidequests
- Visual seeders referencing YOUR photos (drop-in)
- Express API + Vite/React + Electron
- Backblaze B2 (S3) loader (optional)

## Run (dev)
Terminal 1:
```
cd server
npm install
cp ../.env.example ../.env  # (fill B2 creds if using)
npm run dev
```
Terminal 2:
```
cd ../app
npm install
npm run dev
```
Terminal 3 (desktop window):
```
cd ../electron
npm install
npm start
```

## Use Your Photos
Place JPG files under `assets/locations/` matching names in `data/visual_seeders/visuals.json`
(e.g., `user_muertos_market.jpg`). Replace placeholders whenever you're ready.
