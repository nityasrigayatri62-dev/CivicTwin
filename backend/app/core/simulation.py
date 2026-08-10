import sqlite3
import networkx as nx
from typing import Dict, List, Tuple, Any
from app.core.config import settings
from app.db.repositories import CityRepository

def calculate_bpr_travel_time(length_meters: float, speed_limit_kmh: float, volume: float, capacity: float) -> float:
    """
    Calculate travel time in seconds using the Bureau of Public Roads (BPR) formula:
    T = T_free * (1 + alpha * (volume / capacity) ^ beta)
    """
    free_flow_speed_ms = speed_limit_kmh * 1000.0 / 3600.0
    free_flow_time = length_meters / free_flow_speed_ms
    
    # BPR standard coefficients
    alpha = 0.15
    beta = 4.0
    
    congestion_ratio = volume / max(capacity, 1.0)
    travel_time = free_flow_time * (1.0 + alpha * (congestion_ratio ** beta))
    return travel_time

def run_traffic_simulation(
    scenario_type: str = None,
    target_entity_id: str = None,
    parameters: dict = None,
    capacity_boost_roads: Dict[str, float] = None,   # road_id -> capacity multiplier
    speed_boost_roads: Dict[str, float] = None,      # road_id -> speed limit multiplier
    rerouted_transit: Dict[str, List[str]] = None    # transit_id -> new road sequence
) -> Dict[str, Any]:
    """
    Runs an incremental traffic assignment simulation on the Vijayawada network.
    
    Returns:
        Dict: {
            "road_metrics": {road_id: {volume, travel_time, congestion_ratio, availability}},
            "metrics": {average_travel_time_minutes, max_congestion_ratio, congested_roads_count, network_efficiency, failed_commutes_count}
        }
    """
    # 1. Fetch data from DB
    intersections = CityRepository.get_all_intersections()
    roads = CityRepository.get_all_roads()
    zones = CityRepository.get_all_zones()
    facilities = CityRepository.get_all_facilities()
    transit_routes = CityRepository.get_all_transit_routes()
    
    # Map intersections
    node_map = {node["id"]: node for node in intersections}
    
    # 2. Build the simulation road status dictionary
    sim_roads = {}
    for r in roads:
        sim_roads[r["id"]] = {
            "id": r["id"],
            "name": r["name"],
            "start_node": r["start_node"],
            "end_node": r["end_node"],
            "length_meters": r["length_meters"],
            "capacity": r["capacity"],
            "speed_limit_kmh": r["speed_limit_kmh"],
            "road_type": r["road_type"],
            "availability": r["availability"],
            "criticality": r["criticality"],
            "current_volume": 0.0,
            "travel_time_seconds": 0.0
        }
    
    # 3. Apply Scenario Modifications
    surge_factor = 1.0
    if scenario_type:
        if scenario_type == "ROAD_CLOSURE" and target_entity_id:
            if target_entity_id in sim_roads:
                sim_roads[target_entity_id]["availability"] = 0
        elif scenario_type == "ACCIDENT" and target_entity_id:
            # Block the target road where accident occurred, or if target is intersection block connected roads
            if target_entity_id in sim_roads:
                sim_roads[target_entity_id]["availability"] = 0
            else:
                # Target is an intersection, close all incoming/outgoing roads
                for rid, r in sim_roads.items():
                    if r["start_node"] == target_entity_id or r["end_node"] == target_entity_id:
                        r["availability"] = 0
        elif scenario_type == "TRAFFIC_SURGE":
            surge_factor = parameters.get("surge_factor", 1.8) if parameters else 1.8
        elif scenario_type == "WEATHER_EVENT":
            # Reduce speed limit on all roads by e.g. 35%
            speed_reduction = parameters.get("speed_reduction_ratio", 0.35) if parameters else 0.35
            for rid, r in sim_roads.items():
                r["speed_limit_kmh"] = r["speed_limit_kmh"] * (1.0 - speed_reduction)
                
    # 4. Apply Optimization Boosts (from parameters or direct input)
    if capacity_boost_roads:
        for rid, mult in capacity_boost_roads.items():
            if rid in sim_roads:
                sim_roads[rid]["capacity"] *= mult
    if speed_boost_roads:
        for rid, mult in speed_boost_roads.items():
            if rid in sim_roads:
                sim_roads[rid]["speed_limit_kmh"] *= mult

    # 5. Define Travel Demand Matrix
    # We define commute pairs: residential zones -> commercial zones and hospitals/schools
    # Res zones: zone-2 (Patamata: 18000), zone-3 (One Town: 25000), zone-4 (Gunadala: 15000)
    # Total commute demand: ~10% of population is active
    destinations = [
        {"node_id": "node-9", "weight": 0.50, "name": "Labbipet Commercial / NSM School"},
        {"node_id": "node-5", "weight": 0.25, "name": "Gollapudi Commercial"},
        {"node_id": "node-10", "weight": 0.15, "name": "Siddhartha Academy Junction"},
        {"node_id": "node-1", "weight": 0.05, "name": "Benz Circle (Ayush Hospital)"},
        {"node_id": "node-11", "weight": 0.05, "name": "Governorspet (Andhra Hospital)"}
    ]
    
    residential_zones = [
        {"node_id": "node-8", "pop": 18000, "name": "Patamata"},
        {"node_id": "node-14", "pop": 25000, "name": "One Town"},
        {"node_id": "node-13", "pop": 15000, "name": "Gunadala"}
    ]
    
    demands = []
    commute_rate = 0.10 * surge_factor
    for res in residential_zones:
        active_commuters = res["pop"] * commute_rate
        for dest in destinations:
            vol = active_commuters * dest["weight"]
            if vol > 0:
                demands.append({
                    "from": res["node_id"],
                    "to": dest["node_id"],
                    "volume": vol
                })

    # Include Transit Routes demand
    # Each transit route runs buses. Let's say transit routes add a fixed base flow along their stops.
    # Transit Route 1 is Route 10M, Transit Route 2 is Route 20E
    for route in transit_routes:
        route_id = route["id"]
        # Use rerouted roads if provided, otherwise default road sequence
        active_roads = rerouted_transit.get(route_id, route["road_sequence"]) if rerouted_transit else route["road_sequence"]
        
        # Buses add equivalent of 150 personal cars of congestion load due to size and frequent stopping
        bus_car_equivalency = 150.0
        for road_id in active_roads:
            if road_id in sim_roads:
                sim_roads[road_id]["current_volume"] += bus_car_equivalency

    # 6. Incremental Traffic Assignment (3 steps: 35%, 35%, 30%)
    steps = [0.35, 0.35, 0.30]
    failed_commutes_count = 0.0
    total_travel_time_seconds = 0.0
    total_commuters = 0.0
    
    for step_frac in steps:
        # Create a NetworkX DiGraph representing current travel times
        G = nx.DiGraph()
        
        # Add nodes
        for node_id, node in node_map.items():
            G.add_node(node_id, lat=node["latitude"], lng=node["longitude"])
            
        # Add edges (roads)
        for r_id, r in sim_roads.items():
            # If the road is blocked, we do not add it as an edge
            if r["availability"] == 0:
                continue
                
            # Compute travel time at current volume
            t_time = calculate_bpr_travel_time(
                length_meters=r["length_meters"],
                speed_limit_kmh=r["speed_limit_kmh"],
                volume=r["current_volume"],
                capacity=r["capacity"]
            )
            r["travel_time_seconds"] = t_time
            G.add_edge(r["start_node"], r["end_node"], id=r_id, weight=t_time)
            
        # Route this step's fraction of demand
        for demand in demands:
            vol_step = demand["volume"] * step_frac
            total_commuters += vol_step
            
            try:
                # Find shortest path using current travel times
                path = nx.shortest_path(G, source=demand["from"], target=demand["to"], weight="weight")
                
                # Calculate path travel time
                path_time = 0.0
                # Accumulate volume on roads
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    edge_data = G.get_edge_data(u, v)
                    if edge_data:
                        r_id = edge_data["id"]
                        sim_roads[r_id]["current_volume"] += vol_step
                        path_time += sim_roads[r_id]["travel_time_seconds"]
                
                total_travel_time_seconds += path_time * vol_step
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # No path available (islanded nodes due to closure)
                failed_commutes_count += vol_step
                # Add penalty travel time (1 hour = 3600 seconds) for stranded commuters
                total_travel_time_seconds += 3600.0 * vol_step

    # 7. Compute final travel times and metrics
    # Re-calculate travel time for all roads based on final volumes
    congested_roads_count = 0
    max_congestion_ratio = 0.0
    sum_congestion = 0.0
    active_roads_count = 0
    
    for r_id, r in sim_roads.items():
        r["travel_time_seconds"] = calculate_bpr_travel_time(
            length_meters=r["length_meters"],
            speed_limit_kmh=r["speed_limit_kmh"],
            volume=r["current_volume"],
            capacity=r["capacity"]
        )
        
        congestion_ratio = r["current_volume"] / max(r["capacity"], 1.0)
        max_congestion_ratio = max(max_congestion_ratio, congestion_ratio)
        sum_congestion += congestion_ratio
        active_roads_count += 1
        
        if congestion_ratio > 0.8 and r["availability"] == 1:
            congested_roads_count += 1

    # Overall system metrics
    average_travel_time_minutes = (total_travel_time_seconds / max(total_commuters, 1.0)) / 60.0
    
    # Network efficiency score
    # Baseline travel time without congestion or closures is approx 4 minutes
    # Let's scale efficiency: 100% at free flow (~4 mins), decreasing to 0% if travel time exceeds 25 mins
    efficiency = max(0.0, 100.0 - (average_travel_time_minutes - 4.0) * 4.5)
    
    return {
        "road_metrics": {
            r_id: {
                "volume": round(r["current_volume"], 1),
                "travel_time_seconds": round(r["travel_time_seconds"], 1),
                "congestion_ratio": round(r["current_volume"] / r["capacity"], 2),
                "availability": r["availability"]
            }
            for r_id, r in sim_roads.items()
        },
        "metrics": {
            "average_travel_time_minutes": round(average_travel_time_minutes, 2),
            "max_congestion_ratio": round(max_congestion_ratio, 2),
            "congested_roads_count": congested_roads_count,
            "network_efficiency": round(efficiency, 1),
            "failed_commutes_count": int(round(failed_commutes_count))
        }
    }
