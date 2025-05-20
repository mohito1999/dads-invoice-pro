from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Standard form for username/password
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app import crud, schemas
from app.db.session import get_db
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()

@router.post("/access-token", response_model=schemas.Token)
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends() # Username is form_data.username, password is form_data.password
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    'username' field in the form should be the user's email.
    """
    user = await crud.user.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires # Use user.id as subject
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Optional: Add a /password-recovery endpoint later
# Optional: Add a /reset-password endpoint later
