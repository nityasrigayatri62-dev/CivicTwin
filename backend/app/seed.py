import sqlite3
import os
from app.db.database import init_db, get_db_connection

def seed_data():
    print("Initializing Database Schema...")
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing seed data if any (only city structure tables)
    cursor.execute("DELETE FROM transit_routes")
    cursor.execute("DELETE FROM population_zones")
    cursor.execute("DELETE FROM facilities")
    cursor.execute("DELETE FROM roads")
    cursor.execute("DELETE FROM intersections")
    
    # Insert Intersections (Nodes)
    intersections = [
        ("node-1", "Benz Circle", 16.5018, 80.6534),
        ("node-2", "PCR Junction", 16.5141, 80.6206),
        ("node-3", "Ramavarappadu Ring", 16.5173, 80.6725),
        ("node-4", "Varadhi Junction", 16.4883, 80.6289),
        ("node-5", "Gollapudi Junction", 16.5412, 80.5786),
        ("node-6", "PNBS Bus Station", 16.5110, 80.6175),
        ("node-7", "Railway Station Junction", 16.5186, 80.6212),
        ("node-8", "Patamata Junction", 16.5005, 80.6650),
        ("node-9", "Moghalrajpuram Junction", 16.5085, 80.6415),
        ("node-10", "Siddhartha Academy Junction", 16.5025, 80.6480),
        ("node-11", "Governorspet Junction", 16.5150, 80.6280),
        ("node-12", "GND Junction", 16.5200, 80.6400),
        ("node-13", "Gunadala Junction", 16.5230, 80.6620),
        ("node-14", "Kanaka Durga Temple Junction", 16.5155, 80.6060),
        ("node-15", "Guru Nanak Colony Junction", 16.5050, 80.6710)
    ]
    cursor.executemany(
        "INSERT INTO intersections (id, name, latitude, longitude) VALUES (?, ?, ?, ?)",
        intersections
    )
    print(f"Seeded {len(intersections)} intersections.")

    # Insert Roads (Edges)
    # id, name, start_node, end_node, length_meters, capacity, speed_limit_kmh, road_type, availability, current_volume, criticality
    roads = [
        ("road-1", "MG Road PCR-Moghalrajpuram", "node-2", "node-9", 2000.0, 3000.0, 50.0, "ARTERY", 1, 1200.0, 1.5),
        ("road-2", "MG Road Moghalrajpuram-Siddhartha", "node-9", "node-10", 1200.0, 3000.0, 50.0, "ARTERY", 1, 1100.0, 1.4),
        ("road-3", "MG Road Siddhartha-Benz Circle", "node-10", "node-1", 800.0, 3500.0, 50.0, "ARTERY", 1, 1800.0, 1.8),
        ("road-4", "Bandar Road Benz Circle-Patamata", "node-1", "node-8", 1500.0, 3000.0, 50.0, "ARTERY", 1, 1000.0, 1.3),
        ("road-5", "Bandar Road Patamata-Guru Nanak", "node-8", "node-15", 1000.0, 2500.0, 50.0, "ARTERY", 1, 800.0, 1.2),
        ("road-6", "Eluru Road PCR-Governorspet", "node-2", "node-11", 1000.0, 2500.0, 40.0, "ARTERY", 1, 900.0, 1.2),
        ("road-7", "Eluru Road Governorspet-GND", "node-11", "node-12", 1500.0, 2500.0, 40.0, "ARTERY", 1, 950.0, 1.3),
        ("road-8", "Eluru Road GND-Gunadala", "node-12", "node-13", 2200.0, 2000.0, 40.0, "ARTERY", 1, 800.0, 1.1),
        ("road-9", "Eluru Road Gunadala-Ramavarappadu", "node-13", "node-3", 1800.0, 2000.0, 40.0, "ARTERY", 1, 700.0, 1.1),
        ("road-10", "NH16 Benz Circle-Ramavarappadu", "node-1", "node-3", 3200.0, 5000.0, 80.0, "HIGHWAY", 1, 2500.0, 2.5),
        ("road-11", "NH16 Benz Circle-Varadhi", "node-1", "node-4", 2500.0, 5000.0, 80.0, "HIGHWAY", 1, 2200.0, 2.2),
        ("road-12", "Krishna Canal Road PCR-Varadhi", "node-2", "node-4", 3000.0, 2000.0, 50.0, "ARTERY", 1, 700.0, 1.0),
        ("road-13", "PNBS Access Road PNBS-PCR", "node-6", "node-2", 500.0, 3000.0, 40.0, "LOCAL", 1, 1500.0, 1.2),
        ("road-14", "Railway Station Road PNBS-Railway", "node-6", "node-7", 900.0, 2500.0, 40.0, "LOCAL", 1, 1300.0, 1.1),
        ("road-15", "Durga Temple Road PNBS-Durga Temple", "node-6", "node-14", 1200.0, 2000.0, 40.0, "LOCAL", 1, 900.0, 1.1),
        ("road-16", "Gollapudi Bypass Road Durga Temple-Gollapudi", "node-14", "node-5", 4500.0, 3000.0, 60.0, "HIGHWAY", 1, 1100.0, 1.4),
        ("road-17", "Road 17 (Siddhartha Academy Link)", "node-10", "node-1", 900.0, 1200.0, 30.0, "RESIDENTIAL", 1, 400.0, 1.0),
        ("road-18", "Patamata Loop Road Patamata-Siddhartha", "node-8", "node-10", 1300.0, 1500.0, 40.0, "LOCAL", 1, 500.0, 1.0),
        ("road-19", "Moghalrajpuram-GND Link", "node-9", "node-12", 1400.0, 1800.0, 40.0, "LOCAL", 1, 600.0, 1.0),
        ("road-20", "Governorspet Link Road Governorspet-PCR", "node-11", "node-2", 800.0, 2000.0, 40.0, "LOCAL", 1, 800.0, 1.0),
        ("road-21", "Gunadala-Ramavarappadu Ring Link", "node-13", "node-3", 1500.0, 1800.0, 40.0, "LOCAL", 1, 500.0, 1.0),
        ("road-22", "Varadhi-PNBS Link", "node-4", "node-6", 2800.0, 2500.0, 50.0, "LOCAL", 1, 900.0, 1.1),
        ("road-23", "Durga Temple Inner Ring", "node-14", "node-2", 1800.0, 2000.0, 40.0, "LOCAL", 1, 600.0, 1.0),
        ("road-24", "Railway Station-GND Link", "node-7", "node-12", 1800.0, 2200.0, 40.0, "LOCAL", 1, 700.0, 1.0),
        ("road-25", "Guru Nanak Colony Road Guru Nanak-Ramavarappadu", "node-15", "node-3", 2000.0, 1500.0, 40.0, "LOCAL", 1, 450.0, 1.0),
        ("road-26", "Benz Circle-Siddhartha Bypass", "node-1", "node-10", 1000.0, 1500.0, 30.0, "LOCAL", 1, 650.0, 1.0),
        ("road-27", "Moghalrajpuram-Siddhartha Inner Link", "node-9", "node-10", 1100.0, 1200.0, 30.0, "LOCAL", 1, 350.0, 1.0),
        ("road-28", "Ramavarappadu-Patamata Link", "node-3", "node-8", 3500.0, 2200.0, 50.0, "LOCAL", 1, 800.0, 1.1),
        ("road-29", "Gollapudi Industrial Road Gollapudi-PCR", "node-5", "node-2", 6000.0, 2500.0, 60.0, "ARTERY", 1, 1000.0, 1.3),
        ("road-30", "GND-Governorspet Link", "node-12", "node-11", 1100.0, 1500.0, 30.0, "LOCAL", 1, 400.0, 1.0)
    ]
    import json
    # Load matched paths
    paths_file = os.path.join(os.path.dirname(__file__), "matched_paths.json")
    matched_paths = {}
    if os.path.exists(paths_file):
        with open(paths_file, "r") as f:
            matched_paths = json.load(f)
            
    # Add path to road values
    seeded_roads = []
    for r in roads:
        r_id = r[0]
        r_path = matched_paths.get(r_id, [])
        r_path_str = json.dumps(r_path)
        seeded_roads.append(r + (r_path_str,))
        
    cursor.executemany(
        "INSERT INTO roads (id, name, start_node, end_node, length_meters, capacity, speed_limit_kmh, road_type, availability, current_volume, criticality, path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        seeded_roads
    )
    print(f"Seeded {len(roads)} roads with geometry paths.")

    # Insert Facilities
    facilities = [
        ("hospital-1", "Ayush Hospital", "HOSPITAL", 16.5002, 80.6548, "node-1"),
        ("hospital-2", "Andhra Hospital", "HOSPITAL", 16.5162, 80.6308, "node-11"),
        ("school-1", "NSM Public School", "SCHOOL", 16.5105, 80.6382, "node-9"),
        ("school-2", "Siddhartha Public School", "SCHOOL", 16.5028, 80.6472, "node-10"),
        ("fire-station-1", "Vijayawada Central Fire Station", "FIRE_STATION", 16.5182, 80.6188, "node-6"),
        ("police-station-1", "Benz Circle Police Station", "POLICE_STATION", 16.5022, 80.6532, "node-1")
    ]
    cursor.executemany(
        "INSERT INTO facilities (id, name, type, latitude, longitude, nearest_node) VALUES (?, ?, ?, ?, ?, ?)",
        facilities
    )
    print(f"Seeded {len(facilities)} facilities.")

    # Insert Population Zones
    zones = [
        ("zone-1", "Labbipet Commercial Zone", "COMMERCIAL", 16.5050, 80.6390, 400.0, 12000, "node-9"),
        ("zone-2", "Patamata Residential Area", "RESIDENTIAL", 16.4990, 80.6620, 500.0, 18000, "node-8"),
        ("zone-3", "One Town High-Density Area", "RESIDENTIAL", 16.5180, 80.6080, 600.0, 25000, "node-14"),
        ("zone-4", "Gunadala Residential Suburb", "RESIDENTIAL", 16.5250, 80.6650, 500.0, 15000, "node-13"),
        ("zone-5", "Gollapudi Developing Zone", "COMMERCIAL", 16.5380, 80.5850, 800.0, 10000, "node-5")
    ]
    cursor.executemany(
        "INSERT INTO population_zones (id, name, type, latitude, longitude, radius_meters, population, nearest_node) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        zones
    )
    print(f"Seeded {len(zones)} population zones.")

    # Insert Transit Routes
    # Sequence of stops (node/facilities IDs) and sequence of roads (road IDs)
    transit_routes = [
        (
            "transit-1",
            "Route 10M (PNBS - Ramavarappadu via MG Road)",
            "node-6,node-2,node-9,node-10,node-1,node-8,node-3",
            "road-13,road-1,road-2,road-3,road-4,road-28"
        ),
        (
            "transit-2",
            "Route 20E (PNBS - Gunadala via Eluru Road)",
            "node-6,node-7,node-11,node-12,node-13",
            "road-14,road-24,road-30,road-8"
        )
    ]
    cursor.executemany(
        "INSERT INTO transit_routes (id, name, stops_sequence, road_sequence) VALUES (?, ?, ?, ?)",
        transit_routes
    )
    print(f"Seeded {len(transit_routes)} transit routes.")

    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
