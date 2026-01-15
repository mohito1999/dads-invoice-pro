from fastapi import FastAPI
from app.api import api_router  # We will create this soon
from app.core.config import settings # We will create this soon
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import sys
from fastapi import Request
logger = logging.getLogger(__name__) # Get a logger instance


APP_DIR = Path(__file__).resolve().parent 
BASE_DIR = APP_DIR.parent # This is backend/
STATIC_DIR = BASE_DIR / "static" 
# UPLOAD_DIR for saving files will be STATIC_DIR / "uploads"
# (Individual endpoints will handle subdirectories like org_logos, item_images)

# Ensure the base static directory exists (uploads and its subdirs will be created by endpoints)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION
)



app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- BEGIN CORS MIDDLEWARE SETUP ---
# Define a list of origins that are allowed to make cross-origin requests.
# For development, you can allow your frontend's origin.
# For production, you should restrict this to your actual frontend domain(s).
# Using "*" allows all origins, which is okay for local dev but NOT recommended for production.

origins = [
    "http://localhost:5173",  # Your Vite frontend development server
    "http://localhost:3000",  # Common port for other React dev servers
    # Add your deployed frontend URL here when you deploy
    # e.g., "https://your-dad-invoice-app.com" 
]

# If you want to allow all origins (USE WITH CAUTION, especially in production):
# origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True, # Allow cookies to be included in requests (if you use them)
    allow_methods=["*"],    # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allow all headers
)
# --- END CORS MIDDLEWARE SETUP ---

# Ensure settings.API_V1_STR is definitely "/api/v1"
if settings.API_V1_STR != "/api/v1":
    logger.warning(f"WARNING: settings.API_V1_STR is '{settings.API_V1_STR}', expected '/api/v1'. This might affect routing.")

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def read_root():
    # If packaged, this route might be overshadowed by the catch-all below, 
    # but good to keep for API-only mode.
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

# --- STATIC FILE SERVING FOR PACKAGED APP ---
import os
from fastapi.responses import FileResponse

# Check if we are running in a packaged environment or if dist folder exists adjacent
IS_PACKAGED = os.environ.get("IS_PACKAGED_APP") == "True"

# In PyInstaller, sys._MEIPASS is the temp folder where bundles are extracted
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Running as script
    BASE_DIR = Path(__file__).resolve().parent.parent.parent # backend/

FRONTEND_DIST = BASE_DIR / "frontend_dist" # We will rename 'dist' to 'frontend_dist' during build to avoid confusion

if IS_PACKAGED or (FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists()):
    logger.info(f"Serving frontend from {FRONTEND_DIST}")
    
    # Mount assets (js, css, etc.)
    # Vite puts assets in dist/assets
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Catch-all for React Router
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Allow API routes to pass through (they are already matched above if defined)
        if full_path.startswith("api") or full_path.startswith("static"):
             # If it fell through to here, it means no specific API route matched.
             # Return usage 404 for API, or let it fall to 404.
             # But usually starlette routing handles specific routes first.
             pass 

        # Check if specific file exists first (e.g. favicon.ico)
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html
        return FileResponse(FRONTEND_DIST / "index.html")
# --------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is healthy!"}

# You can add more application-wide event handlers here if needed
# e.g., @app.on_event("startup") / @app.on_event("shutdown")