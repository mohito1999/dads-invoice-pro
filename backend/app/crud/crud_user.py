from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from app.models.user import User as UserModel # Alias to avoid name clash
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password # Our security utils


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    """
    Get a user by their ID.
    """
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    """
    Get a user by their email address.
    """
    result = await db.execute(select(UserModel).filter(UserModel.email == email))
    return result.scalars().first()

async def create_user(db: AsyncSession, *, user_in: UserCreate) -> UserModel:
    """
    Create a new user.
    """
    hashed_password = get_password_hash(user_in.password)
    # Create a dictionary for UserModel, excluding the plain password
    # and adding the hashed_password.
    # Pydantic v2: user_data_for_db = user_in.model_dump(exclude={'password'})
    # Pydantic v1: user_data_for_db = user_in.dict(exclude={'password'})

    db_obj_data = user_in.model_dump(exclude={'password'})
    db_obj = UserModel(**db_obj_data, hashed_password=hashed_password)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_user(
    db: AsyncSession, *, db_obj: UserModel, obj_in: UserUpdate
) -> UserModel:
    """
    Update an existing user.
    'db_obj' is the existing user model instance.
    'obj_in' is a Pydantic schema with the update data.
    """
    # Pydantic v2: update_data = obj_in.model_dump(exclude_unset=True)
    # Pydantic v1: update_data = obj_in.dict(exclude_unset=True)
    update_data = obj_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        # If password is being updated, hash the new one
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"] # Don't store plain password
    
    # If email is being updated, ensure it's not already taken by another user
    if "email" in update_data and update_data["email"] != db_obj.email:
        existing_user = await get_user_by_email(db, email=update_data["email"])
        if existing_user and existing_user.id != db_obj.id:
            # This should ideally be raised as an HTTPException in the API layer
            # For now, the CRUD layer might just return the object without updating email
            # or we can raise a ValueError here. Let's prevent update for now.
            # Consider how to signal this error back to the API layer.
            # For simplicity here, we'll just not update the email if it's a conflict.
            # A better approach is to handle this in the API endpoint.
            print(f"Attempt to update email to an existing one: {update_data['email']}") # log this
            del update_data["email"] # Or raise ValueError("Email already registered by another user.")


    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def authenticate_user(
    db: AsyncSession, *, email: str, password: str
) -> UserModel | None:
    """
    Authenticate a user by email and password.
    Returns the user object if authentication is successful, None otherwise.
    """
    user = await get_user_by_email(db, email=email)
    if not user:
        return None
    if not user.is_active: # Optional: check if user is active
        return None # Or raise a specific exception/error code
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def delete_user(db: AsyncSession, *, user_to_delete: UserModel) -> UserModel:
    """
    Delete a user from the database.
    WARNING: This will cascade delete related organizations, customers, items, and invoices
    if the relationships are configured with cascade="all, delete-orphan".
    """
    # The user_to_delete object is already fetched and verified by the API layer
    await db.delete(user_to_delete)
    await db.commit()
    # The object is now detached from the session and effectively deleted from DB.
    # Returning it might be for logging or confirmation, but its relationships might be stale.
    return user_to_delete

