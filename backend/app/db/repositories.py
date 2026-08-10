import json
from app.db.database import get_db_connection

class CityRepository:
    @staticmethod
    def get_all_intersections():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM intersections")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_roads():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM roads")
        rows = cursor.fetchall()
        conn.close()
        roads = []
        for row in rows:
            d = dict(row)
            if d.get("path"):
                try:
                    d["path"] = json.loads(d["path"])
                except Exception:
                    d["path"] = []
            else:
                d["path"] = []
            roads.append(d)
        return roads

    @staticmethod
    def get_all_facilities():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM facilities")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_zones():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM population_zones")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_all_transit_routes():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transit_routes")
        rows = cursor.fetchall()
        conn.close()
        # Parse stops and roads
        routes = []
        for row in rows:
            d = dict(row)
            d["stops_sequence"] = [x.strip() for x in d["stops_sequence"].split(",") if x.strip()]
            d["road_sequence"] = [x.strip() for x in d["road_sequence"].split(",") if x.strip()]
            routes.append(d)
        return routes

    @staticmethod
    def update_road_status(road_id: str, availability: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE roads SET availability = ? WHERE id = ?", (availability, road_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_road_volume(road_id: str, volume: float):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE roads SET current_volume = ? WHERE id = ?", (volume, road_id))
        conn.commit()
        conn.close()

class ScenarioRepository:
    @staticmethod
    def create(scenario_id: str, stype: str, target_id: str, parameters: dict, created_at: str, status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scenarios (id, type, target_entity_id, parameters, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
            (scenario_id, stype, target_id, json.dumps(parameters), created_at, status)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get(scenario_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["parameters"] = json.loads(d["parameters"])
            return d
        return None

class SimulationRepository:
    @staticmethod
    def create(sim_id: str, scenario_id: str, result_metrics: dict, created_at: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO simulations (id, scenario_id, result_metrics, created_at) VALUES (?, ?, ?, ?)",
            (sim_id, scenario_id, json.dumps(result_metrics), created_at)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get(sim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM simulations WHERE id = ?", (sim_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["result_metrics"] = json.loads(d["result_metrics"])
            return d
        return None

class OptimizationRepository:
    @staticmethod
    def create(opt_id: str, simulation_id: str, candidate_plans: list, recommended_plan_id: str, created_at: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO optimizations (id, simulation_id, candidate_plans, recommended_plan_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (opt_id, simulation_id, json.dumps(candidate_plans), recommended_plan_id, created_at)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get(opt_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM optimizations WHERE id = ?", (opt_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["candidate_plans"] = json.loads(d["candidate_plans"])
            return d
        return None

class SystemRepository:
    @staticmethod
    def reset_system():
        conn = get_db_connection()
        cursor = conn.cursor()
        # Reset road statuses and volumes to default
        cursor.execute("UPDATE roads SET availability = 1, current_volume = 0")
        # Clear temporary tables
        cursor.execute("DELETE FROM optimizations")
        cursor.execute("DELETE FROM simulations")
        cursor.execute("DELETE FROM scenarios")
        conn.commit()
        conn.close()
