from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(title="ARGOS V3", version="3.0.9-final")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def ok_token(t: str) -> bool:
    return bool(t and t.startswith("fvJ9-") and len(t) > 20)

@app.get("/")
def root():
    return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.9-final","seed":"argos_ent_pilot_90"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/basins")
def basins(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        return {"error":"Invalid token"}
    return {"basins":[{"id":"midland","name":"Midland"},{"id":"delaware","name":"Delaware"}]}

@app.get("/opportunities")
def opps(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        return {"error":"Invalid token"}
    opp = {
        "id":"CASE_001_MIDLAND_FIREBIRD_54K",
        "basin_id":"midland",
        "county":"Upton",
        "facts":[{"type":"water_production_real","description":"5000 bpd real","evidence_id":"ev_1","snapshot_id":"snap_1"}],
        "inferences":[{"type":"excess","description":"1500 bpd excess"}],
        "verification_status":"PARTIALLY_VERIFIED",
        "decision":"HOLD",
        "temporal_claim":"excess 1500 bpd -> delta 2625 $/day",
        "excess_bpd":1500,
        "delta_per_day":2625
    }
    return {"opportunities":[opp]}

@app.post("/upload/private-data")
def upload(x_tenant_token: Optional[str] = Header(None, alias="X-Tenant-Token")):
    if not ok_token(x_tenant_token or ""):
        return {"error":"Invalid token"}
    return {"status":"uploaded","result":{"excess_bpd":1500,"delta_per_day":2625}}
