"""
Zeroeth Review Backend Server - FastAPI Service
ACS College of Engineering - Department of Aerospace Engineering
"""

import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .kepler_solver import propagate_kepler
from .j2_secular import propagate_with_j2_secular

app = FastAPI(
    title="HEO Trajectory Workbench - Zeroeth Review",
    description="Foundational 2-Body Keplerian Mechanics & J2 Secular Drift Baseline",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASOURCES_DIR = BASE_DIR / "datasources"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

class PropagationRequest(BaseModel):
    semi_major_axis_km: float = 26560.0
    eccentricity: float = 0.72
    inclination_deg: float = 63.435
    raan_deg: float = 45.0
    arg_perigee_deg: float = 270.0
    true_anomaly_deg: float = 0.0
    duration_hours: float = 24.0
    include_j2: bool = False

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "review": "zeroeth_review",
        "engine": "Keplerian Analytical & J2 Baseline"
    }

@app.get("/api/constants")
def get_constants():
    const_file = DATASOURCES_DIR / "earth_constants.json"
    if const_file.exists():
        with open(const_file, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Constants file not found")

@app.get("/api/scenarios")
def get_scenarios():
    scenarios_file = DATASOURCES_DIR / "initial_orbits.json"
    if scenarios_file.exists():
        with open(scenarios_file, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Scenarios file not found")

@app.post("/api/propagate")
def run_propagation(req: PropagationRequest):
    duration_sec = req.duration_hours * 3600.0
    
    # 2-Body Keplerian Baseline
    kepler_res = propagate_kepler(
        a=req.semi_major_axis_km,
        e=req.eccentricity,
        inc_deg=req.inclination_deg,
        raan_deg=req.raan_deg,
        argp_deg=req.arg_perigee_deg,
        nu0_deg=req.true_anomaly_deg,
        duration_sec=duration_sec
    )
    
    response = {
        "scenario_input": req.model_dump(),
        "kepler_baseline": kepler_res,
    }
    
    if req.include_j2:
        j2_res = propagate_with_j2_secular(
            a=req.semi_major_axis_km,
            e=req.eccentricity,
            inc_deg=req.inclination_deg,
            raan0_deg=req.raan_deg,
            argp0_deg=req.arg_perigee_deg,
            nu0_deg=req.true_anomaly_deg,
            duration_sec=duration_sec
        )
        response["j2_secular"] = j2_res
        
    return response

# Serve Frontend static build if it exists
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    def index():
        return {
            "message": "Zeroeth Review API is running. Build the frontend or visit /docs for API schema."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
