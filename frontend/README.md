# Frontend — Enterprise RAG Platform

Next.js (App Router) + TypeScript PWA shell.

## Local development

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Local dev server |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run typecheck` | TypeScript check |

## Notes

- PWA installability and offline shell are Phase 5 backlog items.
- Public API base URL via `NEXT_PUBLIC_API_BASE_URL` (see root `.env.example`).
- Never put secrets in `NEXT_PUBLIC_*` variables.
