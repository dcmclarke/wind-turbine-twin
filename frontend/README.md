# Frontend

React + TypeScript dashboard (Vite, Tailwind, Recharts). It polls
`/api/dashboard` every 2 seconds and `/api/reference-curve` every 5 minutes.

```sh
npm install
npm run dev          # http://localhost:5173, expects the API on http://localhost:8000
npm run build        # type-check and build to dist/
```

Set `VITE_API_URL` to point at a different backend (it is baked in at build time).

- `src/lib/` — API types, formatting, detector labels
- `src/hooks/usePolling.ts` — interval fetching
- `src/components/` — one file per dashboard section
- Colours are CSS variables in `src/index.css`, with separate light and dark values
