import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.repositories import CityRepository, ScenarioRepository, SimulationRepository, OptimizationRepository, SystemRepository
from app.db.database import get_db_connection
from app.core.simulation import run_traffic_simulation
from app.core.optimizer import run_traffic_optimization

router = APIRouter()

class ScenarioCreate(BaseModel):
    type: str
    target_entity_id: str
    parameters: dict = {}

@router.get("/city")
def get_city():
    try:
        intersections = CityRepository.get_all_intersections()
        roads = CityRepository.get_all_roads()
        facilities = CityRepository.get_all_facilities()
        zones = CityRepository.get_all_zones()
        transit = CityRepository.get_all_transit_routes()
        
        return {
            "success": True,
            "data": {
                "intersections": intersections,
                "roads": roads,
                "facilities": facilities,
                "population_zones": zones,
                "transit_routes": transit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DB_ERROR",
                "message": f"Failed to retrieve city data: {str(e)}"
            }
        }

@router.get("/city/roads")
def get_roads():
    try:
        roads = CityRepository.get_all_roads()
        return {"success": True, "data": roads}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DB_ERROR",
                "message": f"Failed to retrieve roads: {str(e)}"
            }
        }

@router.get("/city/facilities")
def get_facilities():
    try:
        facilities = CityRepository.get_all_facilities()
        return {"success": True, "data": facilities}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DB_ERROR",
                "message": f"Failed to retrieve facilities: {str(e)}"
            }
        }

@router.get("/city/transit")
def get_transit():
    try:
        transit = CityRepository.get_all_transit_routes()
        return {"success": True, "data": transit}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DB_ERROR",
                "message": f"Failed to retrieve transit routes: {str(e)}"
            }
        }

@router.post("/scenarios")
def create_scenario(payload: ScenarioCreate):
    try:
        scenario_id = f"scen-{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat()
        
        # Run traffic simulation
        sim_result = run_traffic_simulation(
            scenario_type=payload.type,
            target_entity_id=payload.target_entity_id,
            parameters=payload.parameters
        )
        
        # Store in DB
        ScenarioRepository.create(
            scenario_id=scenario_id,
            stype=payload.type,
            target_id=payload.target_entity_id,
            parameters=payload.parameters,
            created_at=created_at,
            status="COMPLETED"
        )
        
        sim_id = f"sim-{uuid.uuid4().hex[:8]}"
        SimulationRepository.create(
            sim_id=sim_id,
            scenario_id=scenario_id,
            result_metrics=sim_result,
            created_at=created_at
        )
        
        # Update SQLite DB road properties for baseline state (so standard GET calls reflect this)
        # Block closed roads in the database
        if payload.type == "ROAD_CLOSURE" and payload.target_entity_id:
            CityRepository.update_road_status(payload.target_entity_id, 0)
        elif payload.type == "ACCIDENT" and payload.target_entity_id:
            # Check if road or intersection
            roads = CityRepository.get_all_roads()
            road_ids = [r["id"] for r in roads]
            if payload.target_entity_id in road_ids:
                CityRepository.update_road_status(payload.target_entity_id, 0)
            else:
                # Target is an intersection, close all connected roads
                for r in roads:
                    if r["start_node"] == payload.target_entity_id or r["end_node"] == payload.target_entity_id:
                        CityRepository.update_road_status(r["id"], 0)
                        
        # Write simulated road volumes to the database
        for road_id, metrics in sim_result["road_metrics"].items():
            CityRepository.update_road_volume(road_id, metrics["volume"])
            
        return {
            "success": True,
            "data": {
                "scenario_id": scenario_id,
                "simulation_id": sim_id,
                "metrics": sim_result["metrics"],
                "road_metrics": sim_result["road_metrics"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scenario & run simulation: {str(e)}")

@router.post("/simulations/{simulation_id}/optimize")
def optimize_simulation(simulation_id: str):
    try:
        opt_id = f"opt-{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat()
        
        # Run traffic optimization
        opt_result = run_traffic_optimization(simulation_id)
        
        # Save in DB
        OptimizationRepository.create(
            opt_id=opt_id,
            simulation_id=simulation_id,
            candidate_plans=opt_result["candidate_plans"],
            recommended_plan_id=opt_result["recommended_plan_id"],
            created_at=created_at
        )
        
        return {
            "success": True,
            "data": {
                "optimization_id": opt_id,
                "candidate_plans": opt_result["candidate_plans"],
                "recommended_plan_id": opt_result["recommended_plan_id"],
                "narrative": opt_result["narrative"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run traffic optimization: {str(e)}")

@router.get("/scenarios")
def get_scenarios():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scenarios ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        import json
        scenarios = []
        for row in rows:
            d = dict(row)
            d["parameters"] = json.loads(d["parameters"])
            scenarios.append(d)
            
        return {"success": True, "data": scenarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scenarios: {str(e)}")

@router.post("/system/reset")
def reset_system():
    try:
        SystemRepository.reset_system()
        return {"success": True, "message": "System reset completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset system: {str(e)}")

