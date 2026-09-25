# ARGOS V3.0 FINAL - FIX 401
ARGOS Bottleneck Intelligence - V3.0.1 auto-seed

Deploy Backend - Render
Build: pip install -r requirements.txt
Start: uvicorn api.main:app --host 0.0.0.0 --port $PORT
Env: DATABASE_URL, ARGOS_MASTER_SECRET, ARGOS_ADMIN_SECRET, ALLOWED_ORIGINS
