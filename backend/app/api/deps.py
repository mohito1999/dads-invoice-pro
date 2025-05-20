from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.security import decode_token
from app.core.config import settings
from app.db.session import get_db
from app import crud, models, schemas # models will be needed for User model type hint

# This defines the URL where clients will send username/password to get a token
# We will create this endpoint at /api/v1/login/access-token
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    """
    Dependency to get the current user from a JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_token(token)
    if not token_data or not token_data.sub:
        raise credentials_exception
    
    try:
        user_id = uuid.UUID(token_data.sub) # Assuming subject 'sub' in token is user_id as UUID
    except ValueError:
        raise credentials_exception # If 'sub' is not a valid UUID

    user = await crud.user.get_user(db, user_id=user_id)
    if not user:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency to get the current active user.
    Checks if the user obtained from get_current_user is active.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# We can add get_current_active_superuser dependency later if needed for admin actions