from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"status":"LIVE","version":"3.0.7"}

@app.get("/basins")
def basins():
    return {"basins":[{"id":"midland"}]}

@app.get("/opportunities")
def opps():
    return [{"id":"CASE_001","basin_id":"midland"}]

@app.get("/health")
def health():
    return {"ok":True}
