from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import uuid
# Shared properties

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    # is_superuser: bool = False # We can add this later if needed for admin roles

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: constr(min_length=8) # Enforce minimum password length

# Properties to receive via API on update
class UserUpdate(BaseModel): # Allow partial updates
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[constr(min_length=8)] = None
    is_active: Optional[bool] = None

# Properties stored in DB
class UserInDBBase(UserBase):
    id: uuid.UUID
    hashed_password: str

    class Config:
        from_attributes = True

# Additional properties to return to client (never include password)
class User(UserInDBBase):
    # Exclude hashed_password when serializing User model to client
    # Pydantic v2 way to exclude fields in the model definition itself
    # (Alternative is to use response_model_exclude in the endpoint)
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
            }
        }
    }
    # We don't want to send hashed_password to the client
    # This can be handled by how the response_model is defined or
    # by creating a specific UserOut schema without hashed_password.
    # For simplicity, we'll rely on response_model definition in endpoints or a UserOut schema.
    pass

# Schema for user response (without hashed_password)
class UserOut(UserBase):
    id: uuid.UUID
    class Config:
        from_attributes = True


# Schema for token data
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None # 'sub' (subject) is typically user ID or email