from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import hashlib, os

app = FastAPI(title="ARGOS V3", version="3.0.5-final")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def ok_token(t: str) -> bool:
    return t and t.startswith("fvJ9-") and len(t) > 20

@app.get("/")
def root():
    return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.5-final","seed":"argos_ent_pilot_90"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/basins")
def basins(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"basins":[{"id":"midland","name":"Midland"},{"id":"delaware","name":"Delaware"}]}

@app.get("/opportunities")
def get_opps(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        raise HTTPException(status_code=401, detail="Invalid token")
    return [{"id":"CASE_001_MIDLAND_FIREBIRD_54K","basin_id":"midland","county":"Upton","facts":[{"type":"water_production_real","description":"5000 bpd real","evidence_id":"ev_001"}],"verification_status":"PARTIALLY_VERIFIED","decision":"HOLD","temporal_claim":"excess 1500 bpd -> delta 2625 $/day"}]

@app.get("/debug/token")
def debug(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not x_tenant_token:
        return {"error":"no token"}
    return {"hash": hashlib.sha256(x_tenant_token.encode()).hexdigest()[:16], "len": len(x_tenant_token)}

@app.post("/upload/private-data")
def upload(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"status":"uploaded","result":{"excess_bpd":1500,"delta_per_day":2625}}
