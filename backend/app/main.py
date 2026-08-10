from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, city
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# CORS Configuration
# Allowed origins can be configured in settings. Localhost origins are allowed by default for development.
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, prefix="/api")
app.include_router(city.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to CivicTwin API. Go to /docs for API documentation."}
