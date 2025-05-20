from pydantic import BaseModel, HttpUrl, EmailStr, constr
from typing import Optional
import uuid # For UUIDs as primary keys

# Shared properties
class OrganizationBase(BaseModel):
    name: constr(min_length=1, max_length=255)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province_region: Optional[str] = None # More generic term
    zip_code: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[HttpUrl] = None

# Properties to receive on organization creation
class OrganizationCreate(OrganizationBase):
    pass # All fields from OrganizationBase are needed for creation

# Properties to receive on organization update
class OrganizationUpdate(OrganizationBase):
    # All fields are optional for update
    name: Optional[constr(min_length=1, max_length=255)] = None
    # No need to redefine all, Pydantic handles optionality of inherited fields correctly
    # if they are not explicitly re-declared as non-optional.
    # However, to make it explicit that all fields are optional during update:
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province_region: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[HttpUrl] = None


# Properties stored in DB (not directly exposed, but useful for internal representation)
class OrganizationInDBBase(OrganizationBase):
    id: uuid.UUID # Primary Key
    # user_id: uuid.UUID # Foreign Key to User (will add later)
    # created_at: datetime # Will add later with a base model
    # updated_at: datetime # Will add later with a base model

    class Config:
        from_attributes = True # Replaces orm_mode = True in Pydantic v2

# Properties to return to client
class Organization(OrganizationInDBBase):
    pass # Inherits all fields from OrganizationInDBBase

# Properties to return in a list
class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    logo_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True