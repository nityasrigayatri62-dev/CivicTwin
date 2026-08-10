import sqlite3
from app.core.config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Intersections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intersections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
    """)
    
    # Roads
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roads (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start_node TEXT NOT NULL,
            end_node TEXT NOT NULL,
            length_meters REAL NOT NULL,
            capacity REAL NOT NULL,
            speed_limit_kmh REAL NOT NULL,
            road_type TEXT NOT NULL,
            availability INTEGER NOT NULL DEFAULT 1,
            current_volume REAL NOT NULL DEFAULT 0,
            criticality REAL NOT NULL DEFAULT 1.0,
            path TEXT,
            FOREIGN KEY(start_node) REFERENCES intersections(id),
            FOREIGN KEY(end_node) REFERENCES intersections(id)
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE roads ADD COLUMN path TEXT")
    except sqlite3.OperationalError:
        pass

    
    # Facilities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            nearest_node TEXT NOT NULL,
            FOREIGN KEY(nearest_node) REFERENCES intersections(id)
        )
    """)
    
    # Population Zones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS population_zones (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            radius_meters REAL NOT NULL,
            population INTEGER NOT NULL,
            nearest_node TEXT NOT NULL,
            FOREIGN KEY(nearest_node) REFERENCES intersections(id)
        )
    """)
    
    # Transit Routes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transit_routes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            stops_sequence TEXT NOT NULL,
            road_sequence TEXT NOT NULL
        )
    """)
    
    # Scenarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            target_entity_id TEXT,
            parameters TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    # Simulations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            result_metrics TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(scenario_id) REFERENCES scenarios(id)
        )
    """)
    
    # Optimizations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimizations (
            id TEXT PRIMARY KEY,
            simulation_id TEXT NOT NULL,
            candidate_plans TEXT NOT NULL,
            recommended_plan_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(simulation_id) REFERENCES simulations(id)
        )
    """)
    
    conn.commit()
    conn.close()
