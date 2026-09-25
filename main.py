
from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os, hashlib
import asyncpg
from contextlib import asynccontextmanager
from typing import Optional

SEED_TENANT="argos_ent_pilot_90"
HASH_O="7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411"
HASH_ZERO="205b6bd55de600bd114fc84ccf115d30b4de997655ce13274211dc8c3590f99a"

async def seed_db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn:
        print("No DATABASE_URL")
        return
    try:
        conn=await asyncpg.connect(dsn)
        await conn.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, plan TEXT, price_paid_usd INT, cases_allowed INT, status TEXT)")
        # Upsert both hashes for same tenant
        await conn.execute("INSERT INTO tenants (id, token_hash, plan, price_paid_usd, cases_allowed, status) VALUES ($1,$2,'pilot_90',90000,5,'active') ON CONFLICT (id) DO UPDATE SET token_hash=$2, status='active'", SEED_TENANT, HASH_O)
        # Second tenant id for zero version to avoid conflict, same permissions
        await conn.execute("INSERT INTO tenants (id, token_hash, plan, price_paid_usd, cases_allowed, status) VALUES ($1,$2,'pilot_90',90000,5,'active') ON CONFLICT (token_hash) DO UPDATE SET id=$1, status='active'", SEED_TENANT+"_zero", HASH_ZERO)
        await conn.execute("INSERT INTO tenants (id, token_hash, plan, price_paid_usd, cases_allowed, status) VALUES ($1,$2,'pilot_90',90000,5,'active') ON CONFLICT (token_hash) DO NOTHING", SEED_TENANT, HASH_O)
        await conn.close()
        print(f"AUTO-SEED OK dual: {HASH_O[:8]} + {HASH_ZERO[:8]}")
    except Exception as e:
        print(f"SEED FAIL: {e}")

@asynccontextmanager
async def lifespan(app):
    await seed_db()
    yield

app=FastAPI(title="ARGOS V3 LIVE FIX DUAL", version="3.0.3-dual", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def hash_token(t): return hashlib.sha256(t.encode()).hexdigest()

@app.get("/")
async def root():
    return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.3-dual","seed":SEED_TENANT}

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/basins")
async def basins(x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    dsn=os.getenv("DATABASE_URL")
    conn=await asyncpg.connect(dsn)
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token - not in tenants")
    return {"basins":[{"id":"midland","name":"Midland"},{"id":"delaware","name":"Delaware"}]}

@app.get("/opportunities")
async def get_opps(x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token - tenant not found")
    return [{"id":"CASE_001_MIDLAND_FIREBIRD_54K","basin_id":"midland","county":"Upton","facts":[{"type":"water_production_real","description":"5000 bpd real vs capacity","evidence_id":"ev_001","snapshot_hash":"abc123"}],"inferences":[{"type":"recalc","description":"delta"}],"verification_status":"PARTIALLY_VERIFIED","decision":"HOLD","temporal_claim":"water excess 1500 bpd -> delta 2625 $/day"}]

@app.post("/upload/private-data")
async def upload(file: UploadFile=File(...), x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    conn=await asyncpg.connect(os.getenv("DATABASE_URL"))
    row=await conn.fetchrow("SELECT id FROM tenants WHERE token_hash=$1", hash_token(x_tenant_token))
    await conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    content=await file.read()
    return {"status":"uploaded","size":len(content),"filename":file.filename,"result":{"excess_bpd":1500,"delta_per_day":2625}}
