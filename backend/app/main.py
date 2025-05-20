from fastapi import FastAPI
from app.api import api_router  # We will create this soon
from app.core.config import settings # We will create this soon
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION
)

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