import os
from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

class Settings:
    PROJECT_NAME: str = "CivicTwin API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "civictwin.db")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Congestion thresholds
    CONGESTION_THRESHOLD_CLEAR: float = 0.3
    CONGESTION_THRESHOLD_MODERATE: float = 0.7

settings = Settings()
