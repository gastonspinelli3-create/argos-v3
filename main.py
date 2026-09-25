from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"product":"ARGOS V3.0","status":"LIVE","version":"3.0.6-minimal","seed":"argos_ent_pilot_90"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/basins")
def basins():
    return {"basins":[{"id":"midland","name":"Midland"}]}

@app.get("/opportunities")
def opps():
    return [{"id":"CASE_001_MIDLAND_FIREBIRD_54K","basin_id":"midland","county":"Upton","decision":"HOLD","temporal_claim":"excess 1500 bpd -> delta 2625 $/day"}]

@app.post("/upload/private-data")
def upload():
    return {"status":"uploaded","result":{"excess_bpd":1500,"delta_per_day":2625}}
