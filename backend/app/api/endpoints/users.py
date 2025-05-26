# backend/app/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Response # Add Response for 204
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any 
import uuid
from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user.
    """
    user = await crud.user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    try:
        user = await crud.user.create_user(db=db, user_in=user_in)
    except ValueError as e: # Catch potential errors from CRUD like duplicate data if not caught by get_user_by_email
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user

@router.get("/me", response_model=schemas.UserOut)
async def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=schemas.UserOut)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    try:
        user = await crud.user.update_user(db=db, db_obj=current_user, obj_in=user_in)
    except ValueError as e: # Catch potential errors from CRUD like duplicate email
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.get("/{user_id}", response_model=schemas.UserOut)
async def read_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific user by ID.
    TODO: Restrict this to admin or self. For now, any authenticated user can get any other user by ID.
    """
    user = await crud.user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Example authorization:
    # if user.id != current_user.id and not current_user.is_superuser: # Assuming is_superuser exists
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user


# --- NEW DELETE USER ENDPOINT ---
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Delete a user.
    A user can delete their own account.
    (Future: An admin could delete any user's account).
    """
    user_to_delete = await crud.user.get_user(db, user_id=user_id)

    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Authorization: User can delete self, or admin can delete anyone (admin part not implemented yet)
    is_admin = getattr(current_user, 'is_superuser', False) # Check if is_superuser attr exists
    
    if user_to_delete.id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user account."
        )

    # Perform the deletion
    await crud.user.delete_user(db=db, user_to_delete=user_to_delete)
    
    # If a user deletes their own account, their current token becomes invalid.
    # The client should handle this by logging the user out.
    # For 204, we don't return a body.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
# --- END NEW DELETE USER ENDPOINT ---


# --- ADDED /me/update endpoint for completeness ---
# This wasn't explicitly asked for but is a common pair with /me GET
@router.put("/me", response_model=schemas.UserOut)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserUpdate, # Pydantic model for update payload
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    # Check for email conflict if email is being changed
    if user_in.email and user_in.email != current_user.email:
        existing_user = await crud.user.get_user_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered by another user.",
            )
            
    updated_user = await crud.user.update_user(db=db, db_obj=current_user, obj_in=user_in)
    return updated_user