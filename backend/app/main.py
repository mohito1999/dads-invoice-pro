from fastapi import FastAPI
from app.api import api_router  # We will create this soon
from app.core.config import settings # We will create this soon

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION
)

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is healthy!"}

# You can add more application-wide event handlers here if needed
# e.g., @app.on_event("startup") / @app.on_event("shutdown")