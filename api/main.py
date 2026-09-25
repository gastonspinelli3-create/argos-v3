from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os, hashlib
import asyncpg
from contextlib import asynccontextmanager
from typing import Optional

SEED_HASH="7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411"
SEED_TENANT="argos_ent_pilot_90"

async def seed_db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn:
        return
    try:
        conn=await asyncpg.connect(dsn)
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, plan TEXT, price_paid_usd INT, cases_allowed INT, status TEXT)")
        await conn.execute("INSERT INTO tenants (id, token_hash, plan, price_paid_usd, cases_allowed, status) VALUES ($1,$2,'pilot_90',90000,5,'active') ON CONFLICT (id) DO UPDATE SET token_hash=$2, status='active'", SEED_TENANT, SEED_HASH)
        await conn.close()
        print(f"AUTO-SEED OK: {SEED_TENANT}")
    except Exception as e:
        print(f"SEED FAIL: {e}")

@asynccontextmanager
async def lifespan(app):
    await seed_db()
    yield

app=FastAPI(title="ARGOS V3 LIVE FIX", version="3.0.2-live", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def hash_token(t): return hashlib.sha256(t.encode()).hexdigest()

@app.get("/")
async def root():
    return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.2","seed":SEED_TENANT}

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/opportunities")
async def get_opps(x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return [{"id":"CASE_001","basin_id":"midland","status":"live"}]

@app.post("/upload/private-data")
async def upload(file: UploadFile=File(...), x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    content=await file.read()
    return {"status":"uploaded","size":len(content),"filename":file.filename}
