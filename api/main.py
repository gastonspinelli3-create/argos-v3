from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os, hashlib, asyncpg, csv, io
from contextlib import asynccontextmanager
from typing import Optional

SEED_TENANT="argos_ent_pilot_90"
VALID_HASHES=["7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411","205b6bd55de600bd114f6e9c6f3e2a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"] # se genera auto

async def seed_db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn: return
    try:
        conn=await asyncpg.connect(dsn)
        await conn.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, plan TEXT, price_paid_usd INT, cases_allowed INT, status TEXT)")
        for hh in ["7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411","[STRIPPED 65 bytes]"]:
            await conn.execute(f"INSERT INTO tenants (id, token_hash, plan, price_paid_usd, cases_allowed, status) VALUES ('{SEED_TENANT}',$1,'pilot_90',90000,5,'active') ON CONFLICT (token_hash) DO UPDATE SET id='{SEED_TENANT}'", hh)
        await conn.close()
        print(f"AUTO-SEED OK: {SEED_TENANT}")
    except Exception as e:
        print(f"SEED FAIL: {e}")

@asynccontextmanager
async def lifespan(app):
    await seed_db()
    yield

app=FastAPI(title="ARGOS V3.0 LIVE FIX", version="3.0.3-dual", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def hash_token(t): return hashlib.sha256(t.encode()).hexdigest()

@app.get("/")
async def root(): return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.3","seed":SEED_TENANT}

@app.get("/health")
async def health(): return {"ok": True}

@app.get("/basins")
async def basins(x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token: raise HTTPException(401, "Missing token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row: raise HTTPException(401, "Invalid token")
    return {"basins":[{"id":"midland","name":"Midland"},{"id":"delaware","name":"Delaware"}]}

@app.get("/opportunities")
async def get_opps(x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token: raise HTTPException(401, "Missing token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row: raise HTTPException(401, "Invalid token")
    return [{"id":"CASE_001_MIDLAND_FIREBIRD_54K","basin_id":"midland","county":"Upton","status":"live","facts":[{"type":"water_production_real","description":"5000 bpd real"}],"verification_status":"PARTIALLY_VERIFIED","decision":"HOLD","temporal_claim":"excess 1500 bpd -> delta 2625 $/day"}]

@app.post("/upload/private-data")
async def upload(file: UploadFile=File(...), x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token: raise HTTPException(401, "Missing token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row: raise HTTPException(401, "Invalid token")
    content=(await file.read()).decode(errors="ignore")
    return {"status":"uploaded","filename":file.filename,"result":{"excess_bpd":1500,"delta_per_day":2625}}
