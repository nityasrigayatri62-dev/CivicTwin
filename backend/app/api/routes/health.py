from fastapi import APIRouter
import sqlite3
import os
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def get_health():
    # Test database connectivity
    db_connected = False
    try:
        conn = sqlite3.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        db_connected = True
        conn.close()
    except Exception:
        pass

    map_configured = bool(settings.GOOGLE_MAPS_API_KEY)
    ai_configured = bool(settings.GEMINI_API_KEY)
    
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "db_connected": db_connected,
            "map_configured": map_configured,
            "ai_configured": ai_configured,
            "ai_mode": "live" if ai_configured else "fallback",
            "congestion_thresholds": {
                "clear": settings.CONGESTION_THRESHOLD_CLEAR,
                "moderate": settings.CONGESTION_THRESHOLD_MODERATE
            }
        }
    }
