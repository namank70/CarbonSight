# ClimateChain Frontend (React + Vite)

## 1) Install
```bash
npm install
```

## 2) Configure API
Create a `.env` file (same folder as package.json):
```env
VITE_API_URL=http://localhost:8000
```

## 3) Run
```bash
npm run dev
```

## Notes
- If you do not create a `.env` file, the frontend falls back to `http://localhost:8000`.
- This project expects your backend FastAPI to expose:
  - `GET /metadata`
  - `POST /analyze/{category}`
- Replace the placeholder images in `src/assets/` with your real ones if you want.
