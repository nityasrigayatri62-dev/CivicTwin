import json
import urllib.request
import urllib.error
from typing import Dict, List, Any
from app.core.config import settings
from app.db.repositories import ScenarioRepository, SimulationRepository, OptimizationRepository, CityRepository
from app.core.simulation import run_traffic_simulation

def call_gemini_api(prompt: str) -> str:
    """
    Calls the Gemini API directly using urllib.request to avoid external SDK dependencies.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return ""
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            # Extract text content from Gemini response structure
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
    except Exception as e:
        print(f"Failed to call Gemini API: {str(e)}")
    return ""

def run_traffic_optimization(simulation_id: str) -> Dict[str, Any]:
    """
    Evaluates 3 traffic mitigation plans for a given simulation run and recommends the best one.
    
    Plans:
    1. Transit Rerouting: Reroute public transit paths to bypass congested or blocked roads.
    2. Signal Timing Coordination: Increase capacity (+25%) of the top alternative roads.
    3. Dynamic Speed Limits: Boost speed limit on high-capacity bypass highways.
    """
    sim = SimulationRepository.get(simulation_id)
    if not sim:
        raise ValueError(f"Simulation {simulation_id} not found.")
        
    scen = ScenarioRepository.get(sim["scenario_id"])
    if not scen:
        raise ValueError(f"Scenario for simulation {simulation_id} not found.")
        
    scenario_type = scen["type"]
    target_entity_id = scen["target_entity_id"]
    parameters = scen["parameters"]
    
    # Identify congested roads from simulation
    road_metrics = sim["result_metrics"]["road_metrics"]
    congested_roads = [rid for rid, m in road_metrics.items() if m["congestion_ratio"] > 0.7 and m["availability"] == 1]
    
    # ----------------------------------------------------
    # PLAN 1: Transit Rerouting
    # ----------------------------------------------------
    # If the target closed road is part of public transit road sequences, we reroute the route.
    # In a simplified version, we just route the transit routes avoiding the closed/congested roads.
    rerouted_transit = {}
    transit_routes = CityRepository.get_all_transit_routes()
    
    # We find if any transit routes use the blocked/congested road
    blocked_roads = [target_entity_id] if scenario_type in ["ROAD_CLOSURE", "ACCIDENT"] else []
    roads_to_avoid = blocked_roads + congested_roads
    
    for route in transit_routes:
        route_id = route["id"]
        # If route intersects with blocked roads, we reroute.
        # Rerouting drops the blocked/congested roads and replaces them by alternative path
        orig_seq = route["road_sequence"]
        new_seq = [r for r in orig_seq if r not in roads_to_avoid]
        # Fallback if too many roads blocked: just use default road sequence minus closed roads
        if not new_seq:
            new_seq = [r for r in orig_seq if r not in blocked_roads]
        rerouted_transit[route_id] = new_seq
        
    plan1_res = run_traffic_simulation(
        scenario_type=scenario_type,
        target_entity_id=target_entity_id,
        parameters=parameters,
        rerouted_transit=rerouted_transit
    )
    
    # ----------------------------------------------------
    # PLAN 2: Signal Timing Coordination (Capacity Boost)
    # ----------------------------------------------------
    # Boost capacity on alternative paths. We identify the top 4 alternative routes that are currently
    # carrying traffic but aren't blocked, and boost their capacity by 25%.
    alternative_roads = []
    for rid, m in road_metrics.items():
        if rid != target_entity_id and m["availability"] == 1 and m["volume"] > 100:
            alternative_roads.append((rid, m["congestion_ratio"]))
            
    # Sort by congestion (highest first to target bottlenecks)
    alternative_roads.sort(key=lambda x: x[1], reverse=True)
    top_boost_roads = {rid: 1.25 for rid, _ in alternative_roads[:4]}
    
    plan2_res = run_traffic_simulation(
        scenario_type=scenario_type,
        target_entity_id=target_entity_id,
        parameters=parameters,
        capacity_boost_roads=top_boost_roads
    )
    
    # ----------------------------------------------------
    # PLAN 3: Dynamic Speed Limits
    # ----------------------------------------------------
    # Increase the speed limit on alternative routes (highways or major arterials) by 20%
    # to pull traffic away from residential areas.
    speed_boost_roads = {}
    all_roads = CityRepository.get_all_roads()
    for r in all_roads:
        if r["road_type"] in ["HIGHWAY", "ARTERY"] and r["id"] != target_entity_id:
            speed_boost_roads[r["id"]] = 1.20
            
    plan3_res = run_traffic_simulation(
        scenario_type=scenario_type,
        target_entity_id=target_entity_id,
        parameters=parameters,
        speed_boost_roads=speed_boost_roads
    )
    
    # ----------------------------------------------------
    # COMPILING CANDIDATE PLANS
    # ----------------------------------------------------
    candidate_plans = [
        {
            "plan_id": "plan-1",
            "name": "Transit Rerouting",
            "description": "Reroutes Transit Route 10M and 20E to bypass congested junctions. This reduces heavy vehicle bottlenecking and opens up road space on key corridors.",
            "metrics": plan1_res["metrics"]
        },
        {
            "plan_id": "plan-2",
            "name": "Signal Timing Coordination & Dynamic Lanes",
            "description": "Optimizes green-light durations at critical junctions along alternative routes and opens hard-shoulder lanes. This boosts road capacity by 25% on alternative corridors.",
            "metrics": plan2_res["metrics"]
        },
        {
            "plan_id": "plan-3",
            "name": "Dynamic Speed Limit Management",
            "description": "Increases speed limits by 20% on the NH16 Highway and major bypass arterials to draw commuter flow away from congested local and residential networks.",
            "metrics": plan3_res["metrics"]
        }
    ]
    
    # Find the recommended plan (lowest average travel time)
    recommended_plan = min(candidate_plans, key=lambda x: x["metrics"]["average_travel_time_minutes"])
    recommended_plan_id = recommended_plan["plan_id"]
    
    # ----------------------------------------------------
    # GENERATING PLANNER NARRATIVE (GEMINI OR FALLBACK)
    # ----------------------------------------------------
    prompt = f"""
    You are an expert Urban Mobility Planner and AI Assistant for the CivicTwin Digital Twin Platform.
    
    You have simulated traffic for the city of Vijayawada under a scenario of type '{scenario_type}' affecting entity '{target_entity_id}'.
    The baseline average travel time was {sim["result_metrics"]["metrics"]["average_travel_time_minutes"]} minutes.
    
    We evaluated three candidate mitigation plans:
    1. Transit Rerouting (Plan 1): Avg Travel Time = {plan1_res["metrics"]["average_travel_time_minutes"]} mins, Efficiency = {plan1_res["metrics"]["network_efficiency"]}%
    2. Signal Timing Coordination (Plan 2): Avg Travel Time = {plan2_res["metrics"]["average_travel_time_minutes"]} mins, Efficiency = {plan2_res["metrics"]["network_efficiency"]}%
    3. Dynamic Speed Limits (Plan 3): Avg Travel Time = {plan3_res["metrics"]["average_travel_time_minutes"]} mins, Efficiency = {plan3_res["metrics"]["network_efficiency"]}%
    
    The recommended plan is '{recommended_plan["name"]}'.
    
    Provide a professional, structured evaluation report (under 300 words) in markdown format. 
    Include:
    - **Executive Recommendation**: State clearly why '{recommended_plan["name"]}' is the best choice based on metrics.
    - **Impact Analysis**: Explain how it redistributes traffic and relieves congestion compared to the other plans.
    - **Actionable Steps**: List 3 immediate deployment steps for the traffic control center.
    - **Digital Twin Value**: A brief statement on why simulating this before physical deployment was crucial to avoid gridlock.
    
    Make it highly engaging, professional, and omit greetings or markdown titles (start directly with the executive recommendation). Use clean formatting.
    """
    
    narrative = call_gemini_api(prompt)
    
    if not narrative:
        # Fallback rule-based narrative
        improvement = round((1 - recommended_plan["metrics"]["average_travel_time_minutes"] / sim["result_metrics"]["metrics"]["average_travel_time_minutes"]) * 100, 1)
        narrative = f"""### Executive Recommendation
The AI Optimizer strongly recommends **{recommended_plan['name']}** to mitigate the traffic disruption caused by the active {scenario_type.replace('_', ' ').title()} event. This plan achieves an average travel time of **{recommended_plan['metrics']['average_travel_time_minutes']} minutes** (a **{improvement}% improvement** over the unmitigated scenario) and restores network efficiency to **{recommended_plan['metrics']['network_efficiency']}%**.

### Impact Analysis
* **{recommended_plan['name']}** outperforms other candidates by targeting the core bottleneck. 
* By dynamically adjusting system capacity or routing paths, it disperses traffic before major delays propagate back into the central arterials.
* Stranded commuter volumes are reduced, and the maximum congestion ratio is capped at **{recommended_plan['metrics']['max_congestion_ratio']}**.

### Actionable Deployment Steps
1. **Activate Intelligent Signal Phasing**: Re-allocate green times along alternative bypass corridors to maximize throughput.
2. **Alert Transit Services**: Dispatch the updated routing map to public transit drivers and update digital schedules at bus shelters.
3. **Variable Message Signs (VMS)**: Deploy digital signs at node entries directing drivers to the recommended alternate routes.

### Digital Twin Value
Testing these parameters in the **CivicTwin** virtual environment saved Vijayawada from trial-and-error changes on active streets, preventing potential gridlock on NH16 and MG Road.
"""

    return {
        "candidate_plans": candidate_plans,
        "recommended_plan_id": recommended_plan_id,
        "narrative": narrative
    }
