from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import uuid

# Shared properties for a customer
class CustomerBase(BaseModel):
    company_name: constr(min_length=1, max_length=255)
    poc_name: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state_province_region: Optional[str] = None
    billing_zip_code: Optional[str] = None
    billing_country: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    # whatsapp_number: Optional[str] = None # For bot communication later

# Properties to receive on customer creation
class CustomerCreate(CustomerBase):
    # company_name is mandatory from CustomerBase
    organization_id: uuid.UUID # Customer must belong to an organization

# Properties to receive on customer update (all fields optional)
class CustomerUpdate(BaseModel): # Explicitly make all fields optional for update
    company_name: Optional[constr(min_length=1, max_length=255)] = None
    poc_name: Optional[str] = None
    billing_address_line1: Optional[str] = None
    billing_address_line2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state_province_region: Optional[str] = None
    billing_zip_code: Optional[str] = None
    billing_country: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    # organization_id: Optional[uuid.UUID] = None # Usually, org link doesn't change, or is handled carefully

# Properties stored in DB
class CustomerInDBBase(CustomerBase):
    id: uuid.UUID
    organization_id: uuid.UUID # Foreign Key to Organization

    class Config:
        from_attributes = True

# Properties to return to client
class Customer(CustomerInDBBase):
    pass # Inherits all fields

# Summary for lists
class CustomerSummary(BaseModel):
    id: uuid.UUID
    company_name: str
    poc_name: Optional[str] = None
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True