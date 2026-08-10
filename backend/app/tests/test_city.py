import pytest
import requests

def test_health():
    response = requests.get("http://127.0.0.1:8000/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["db_connected"] is True

def test_city_baseline():
    response = requests.get("http://127.0.0.1:8000/api/city")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    city = data["data"]
    assert "roads" in city
    assert "intersections" in city
    assert "facilities" in city
    assert "population_zones" in city
    assert "transit_routes" in city
    
    # Assert counts match our seed data
    assert len(city["intersections"]) == 15
    assert len(city["roads"]) == 30
    assert len(city["facilities"]) == 6
    assert len(city["population_zones"]) == 5
    assert len(city["transit_routes"]) == 2

    # Check for Road 17
    road_17 = next((r for r in city["roads"] if r["id"] == "road-17"), None)
    assert road_17 is not None
    assert road_17["name"] == "Road 17 (Siddhartha Academy Link)"
    assert "path" in road_17
    assert isinstance(road_17["path"], list)
    assert len(road_17["path"]) > 0
    assert "lat" in road_17["path"][0]
    assert "lng" in road_17["path"][0]


def test_scenario_simulation_optimization_flow():
    # 1. Create a road closure scenario
    payload = {
        "type": "ROAD_CLOSURE",
        "target_entity_id": "road-1",
        "parameters": {}
    }
    response = requests.post("http://127.0.0.1:8000/api/scenarios", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    scen_data = data["data"]
    sim_id = scen_data["simulation_id"]
    assert sim_id is not None
    assert "metrics" in scen_data
    assert "road_metrics" in scen_data
    
    # 2. Verify database updated and road-1 is blocked
    response = requests.get("http://127.0.0.1:8000/api/city")
    assert response.status_code == 200
    city = response.json()["data"]
    road_1 = next((r for r in city["roads"] if r["id"] == "road-1"), None)
    assert road_1 is not None
    assert road_1["availability"] == 0
    
    # 3. Run Optimization
    response = requests.post(f"http://127.0.0.1:8000/api/simulations/{sim_id}/optimize")
    assert response.status_code == 200
    opt_data = response.json()
    assert opt_data["success"] is True
    assert "candidate_plans" in opt_data["data"]
    assert opt_data["data"]["recommended_plan_id"] is not None
    assert "narrative" in opt_data["data"]
    
    # 4. Reset System
    response = requests.post("http://127.0.0.1:8000/api/system/reset")
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 5. Verify road-1 is back online
    response = requests.get("http://127.0.0.1:8000/api/city")
    assert response.status_code == 200
    city = response.json()["data"]
    road_1 = next((r for r in city["roads"] if r["id"] == "road-1"), None)
    assert road_1 is not None
    assert road_1["availability"] == 1

