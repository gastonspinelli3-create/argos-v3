# ARGOS V3.0 FINAL - CLOSED

ARGOS Bottleneck Intelligence - V3.0 con FORCE RLS x5 + recalc dinámica sin hardcode

## Deploy

### Backend - Render
Build: pip install -r requirements.txt
Start: uvicorn api.main:app --host 0.0.0.0 --port $PORT

Env:
DATABASE_URL=postgres://...
ARGOS_MASTER_SECRET=...
ARGOS_ADMIN_SECRET=...
ALLOWED_ORIGINS=https://...

Migration:
psql $DATABASE_URL -f schema.sql

### Frontend - GitHub Pages / Vercel
Static: index.html
Set API URL to your Render URL
