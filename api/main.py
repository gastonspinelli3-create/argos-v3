from fastapi import FastAPI, Depends, Header, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os, hashlib, json, uuid
from datetime import datetime, timezone
from typing import Optional, List
from cryptography.fernet import Fernet
import asyncpg
from contextlib import asynccontextmanager

def require_env(n):
    v=os.getenv(n)
    if not v: raise RuntimeError(f"Missing {n}")
    return v
def get_master_secret(): return require_env("ARGOS_MASTER_SECRET")
def get_admin_secret(): return require_env("ARGOS_ADMIN_SECRET")
def get_allowed_origins():
    raw=os.getenv("ALLOWED_ORIGINS","")
    if not raw: return ["http://localhost:3000"]
    return [o.strip() for o in raw.split(",") if o.strip()]

SEED_TOKEN="fvJ9-OwYEY9qtoUgtxX0xyGC4ZVmH_Rjx2tRtp4F-qI"
SEED_HASH="7be066312bd91c7faa402bfac63ddea16de0fab589b53aba564e79b9c9b82411"
SEED_TENANT="argos_ent_pilot_90"

async def seed_db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn: return
    try:
        conn=await asyncpg.connect(dsn)
        await conn.execute("""CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, plan TEXT, tier_name TEXT, status TEXT, live_until TIMESTAMPTZ, access_until TIMESTAMPTZ, founding_license BOOLEAN, token_hash TEXT UNIQUE, kms_key_id TEXT, price_paid_usd INT, cases_allowed INT, basins_allowed INT, features JSONB);""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS tenant_basins (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE, basin_id TEXT, basin_name TEXT, UNIQUE(tenant_id, basin_id));""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT, action TEXT, request_id TEXT, timestamp TIMESTAMPTZ DEFAULT NOW());""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS evidence_sources (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), source_type TEXT, url TEXT, title TEXT);""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS opportunities (id TEXT PRIMARY KEY, basin_id TEXT, basin_name TEXT, tier_required TEXT, tier_min_price INT, county TEXT, operator TEXT, facts JSONB, inferences JSONB, hypothesis TEXT, unknown_data JSONB, opportunity_statement TEXT, what_collected JSONB, how_connected TEXT, what_you_had_not_seen TEXT, verification_notes TEXT, temporal_claim TEXT, temporal_evidence_id UUID, bwpd_projected JSONB, verification_status TEXT, public_evidence_count INT, decision TEXT, created_at TIMESTAMPTZ DEFAULT NOW());""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS user_private_uploads (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE, basin_id TEXT, opportunity_id TEXT, upload_type TEXT, filename TEXT, mime_type TEXT, size_bytes INT, data_encrypted TEXT, parsed_summary JSONB, created_at TIMESTAMPTZ DEFAULT NOW());""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS opportunity_recalculations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE, opportunity_id TEXT, private_upload_ids UUID[], verification_status TEXT, public_evidence INT, private_evidence INT, remaining_unknowns INT, calculation_status TEXT, result JSONB, algorithm_version TEXT, request_id TEXT, created_at TIMESTAMPTZ DEFAULT NOW());""")
        await conn.execute("INSERT INTO tenants (id, plan, tier_name, status, live_until, access_until, founding_license, token_hash, kms_key_id, price_paid_usd, cases_allowed, basins_allowed, features) VALUES ($1,'pilot_90','Starter','active',NOW()+INTERVAL '90 days',NOW()+INTERVAL '90 days',false,$2,'kms_90',90000,5,1,'{}'::jsonb) ON CONFLICT (id) DO UPDATE SET token_hash=EXCLUDED.token_hash", SEED_TENANT, SEED_HASH)
        await conn.execute("INSERT INTO tenant_basins (tenant_id, basin_id, basin_name) VALUES ($1,'midland','Midland Basin') ON CONFLICT (tenant_id, basin_id) DO NOTHING", SEED_TENANT)
        await conn.execute("INSERT INTO evidence_sources (id, source_type, url, title) VALUES ('00000000-0000-0000-0000-000000000001','ENERGYNOW','https://energynow.com','FireBird') ON CONFLICT (id) DO NOTHING")
        await conn.execute("INSERT INTO opportunities (id, basin_id, basin_name, tier_required, tier_min_price, county, operator, facts, inferences, hypothesis, unknown_data, opportunity_statement, what_collected, how_connected, what_you_had_not_seen, verification_notes, temporal_claim, temporal_evidence_id, bwpd_projected, verification_status, public_evidence_count, decision) VALUES ('CASE_001_MIDLAND_FIREBIRD_54K','midland','Midland Basin','pilot_90',90000,'Upton','Continental Resources','[]'::jsonb,'[]'::jsonb,'test','[]'::jsonb,'OPORTUNIDAD','[]'::jsonb,'cruce','no vista','verificar','Aug 2026','00000000-0000-0000-0000-000000000001','{}'::jsonb,'PARTIALLY_VERIFIED',1,'REFORMULAR') ON CONFLICT (id) DO NOTHING")
        await conn.close()
        print(f"AUTO-SEED OK {SEED_TENANT}")
    except Exception as e:
        print(f"SEED FAIL {e}")

@asynccontextmanager
async def lifespan(app):
    await seed_db()
    yield

app=FastAPI(title="ARGOS V3.0 FINAL FIX 401", version="3.0.1-auto-seed", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_allowed_origins(), allow_credentials=True, allow_methods=["GET","POST"], allow_headers=["X-Tenant-Token","X-Admin-Secret","Content-Type","X-Request-Id"])

async def get_db():
    dsn=os.getenv("DATABASE_URL")
    if not dsn: raise HTTPException(status_code=500, detail="DATABASE_URL missing")
    conn=await asyncpg.connect(dsn)
    try: yield conn
    finally: await conn.close()

def hash_token(t): return hashlib.sha256(t.encode()).hexdigest()

async def get_current_tenant(request: Request, x_tenant_token: Optional[str]=Header(None, alias="X-Tenant-Token"), db=Depends(get_db)):
    if not x_tenant_token: raise HTTPException(status_code=401, detail="Missing X-Tenant-Token")
    th=hash_token(x_tenant_token)
    row=await db.fetchrow("SELECT id, plan, tier_name, status, live_until, access_until, founding_license, price_paid_usd, cases_allowed, basins_allowed FROM tenants WHERE token_hash=$1", th)
    if not row: raise HTTPException(status_code=401, detail="Invalid token - tenant not found")
    return dict(row), request.headers.get("X-Request-Id", str(uuid.uuid4()))

@app.get("/")
async def root(tenant_payload=Depends(get_current_tenant)):
    tenant, req_id=tenant_payload
    return {"product":"ARGOS V3.0 FINAL FIX 401","tenant":tenant["id"],"seed_fix":"auto-seed 401 applied","request_id":req_id}

@app.get("/basins")
async def list_basins(tenant_payload=Depends(get_current_tenant), db=Depends(get_db)):
    tenant, req_id=tenant_payload
    rows=await db.fetch("SELECT basin_id, basin_name FROM tenant_basins WHERE tenant_id=$1", tenant["id"])
    return {"tenant":tenant["id"],"basins":[dict(r) for r in rows],"request_id":req_id}

@app.get("/opportunities")
async def get_opportunities(tenant_payload=Depends(get_current_tenant), db=Depends(get_db)):
    tenant, req_id=tenant_payload
    allowed=await db.fetch("SELECT basin_id FROM tenant_basins WHERE tenant_id=$1", tenant["id"])
    basins=[r["basin_id"] for r in allowed]
    opps=await db.fetch("SELECT * FROM opportunities WHERE basin_id=ANY($1) AND tier_min_price<=$2", basins, tenant["price_paid_usd"])
    return {"tenant":tenant["id"],"opportunities":[dict(o) for o in opps],"request_id":req_id}

@app.post("/upload/private-data")
async def upload_private_data(request: Request, file: UploadFile=File(...), upload_type: str=Form(...), basin_id: Optional[str]=Form(None), opportunity_id: Optional[str]=Form(None), tenant_payload=Depends(get_current_tenant), db=Depends(get_db)):
    tenant, req_id=tenant_payload
    content=await file.read()
    text=content.decode('utf-8', errors='ignore').lower()
    import re
    def extract(kws):
        for kw in kws:
            m=re.search(rf"{kw}[^\d]*([\d,]+\.?\d*)", text)
            if m:
                try: return float(m.group(1).replace(',',''))
                except: pass
        return None
    water=extract(["water.*production","bwpd"])
    swd=extract(["swd.*capacity"])
    trucking=extract(["trucking.*cost","trucking"])
    recycling=extract(["recycling.*cost","recycling"])
    excess=max(0, water-swd) if water and swd else water
    delta=excess*(trucking-recycling) if excess and trucking and recycling else None
    parsed={"values":{"water":water,"swd":swd,"trucking":trucking,"recycling":recycling}}
    async with db.transaction():
        up=await db.fetchrow("INSERT INTO user_private_uploads (tenant_id, basin_id, opportunity_id, upload_type, filename, mime_type, size_bytes, data_encrypted, parsed_summary) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id", tenant["id"], basin_id, opportunity_id or "CASE_001_MIDLAND_FIREBIRD_54K", upload_type, file.filename, file.content_type or "text/csv", len(content), "enc", json.dumps(parsed))
        result={"excess_bpd":excess,"delta_per_day":delta,"parsed_values":parsed}
        rec=await db.fetchrow("INSERT INTO opportunity_recalculations (tenant_id, opportunity_id, private_upload_ids, verification_status, public_evidence, private_evidence, remaining_unknowns, calculation_status, result, algorithm_version, request_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING id", tenant["id"], opportunity_id or "CASE_001_MIDLAND_FIREBIRD_54K", [up["id"]], "ENHANCED", 1, 1, 0, "CALCULABLE_WITH_PRIVATE_DATA", json.dumps(result), "v3.0.1-auto-seed", req_id)
    return {"status":"uploaded_and_recalculated","upload_id":str(up["id"]),"result":result,"recalculation_id":str(rec["id"]),"request_id":req_id}

@app.get("/admin/seed")
async def admin_seed(x_admin_secret: str=Header(..., alias="X-Admin-Secret"), db=Depends(get_db)):
    if x_admin_secret!=get_admin_secret(): raise HTTPException(status_code=403, detail="Admin only")
    await seed_db()
    rows=await db.fetch("SELECT id FROM tenants")
    return {"seeded":True,"tenants":[dict(r) for r in rows]}
