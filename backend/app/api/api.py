from fastapi import APIRouter

# Import endpoint modules
from app.api.endpoints import organizations # <--- IMPORT organizations ROUTER MODULE
from app.api.endpoints import login # <--- IMPORT login ROUTER MODULE
from app.api.endpoints import users # <--- IMPORT users ROUTER MODULE


api_router = APIRouter()

# Include other routers here
api_router.include_router(login.router, prefix="/login", tags=["Login"]) 
api_router.include_router(users.router, prefix="/users", tags=["Users"]) 
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"]) # <--- INCLUDE ROUTER
# Example for future:
# from .endpoints import users, items
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(items.router, prefix="/items", tags=["Items"])


@api_router.get("/test", tags=["Test"]) # This was our initial test endpoint
async def test_endpoint():
    return {"message": "API router is working!"}