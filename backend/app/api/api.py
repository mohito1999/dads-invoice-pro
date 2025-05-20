from fastapi import APIRouter

api_router = APIRouter()

# We will include other routers here later, for example:
# from .endpoints import items, users, organizations
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
# api_router.include_router(items.router, prefix="/items", tags=["Items"])

# For now, let's add a simple test endpoint to this router
@api_router.get("/test", tags=["Test"])
async def test_endpoint():
    return {"message": "API router is working!"}