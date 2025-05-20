from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any # Any for return type hint flexibility
import uuid
from app import crud, models, schemas # models for type hint, schemas for validation/response
from app.db.session import get_db
from app.api import deps # Our dependencies, e.g., get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserCreate,
    # This endpoint could be protected later to be admin-only if needed
    # current_user: models.User = Depends(deps.get_current_active_superuser) # Example
) -> Any:
    """
    Create new user.
    For now, this is an open endpoint. Later, you might restrict it.
    """
    user = await crud.user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user = await crud.user.create_user(db=db, user_in=user_in)
    return user

@router.get("/me", response_model=schemas.UserOut)
async def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.get("/{user_id}", response_model=schemas.UserOut)
async def read_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user) # Ensure requester is authenticated
) -> Any:
    """
    Get a specific user by ID.
    (Could be restricted to admin or self in future)
    """
    user = await crud.user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Add authorization logic here if needed, e.g. only admin or self can access
    # if user.id != current_user.id and not current_user.is_superuser:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user

# You can add more user management endpoints here later:
# - List users (admin only)
# - Update user (self or admin)
# - Delete user (admin only)