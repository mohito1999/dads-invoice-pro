# backend/app/schemas/invoice_template.py
from pydantic import BaseModel, constr
from typing import Optional
import uuid

# Shared base properties
class InvoiceTemplateBase(BaseModel):
    name: constr(min_length=1, max_length=255)
    description: Optional[str] = None
    template_file_path: constr(min_length=1, max_length=255) # e.g., "modern_template.html"
    thumbnail_url: Optional[str] = None # Optional URL for a preview image
    is_system_default: Optional[bool] = False
    order_index: Optional[int] = 0

# Properties to receive on template creation
class InvoiceTemplateCreate(InvoiceTemplateBase):
    pass # All fields from Base are required for creation, or have defaults

# Properties to receive on template update (all fields optional)
class InvoiceTemplateUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=255)] = None
    description: Optional[str] = None
    template_file_path: Optional[constr(min_length=1, max_length=255)] = None
    thumbnail_url: Optional[str] = None
    is_system_default: Optional[bool] = None
    order_index: Optional[int] = None

# Properties stored in DB (includes ID)
class InvoiceTemplateInDBBase(InvoiceTemplateBase):
    id: uuid.UUID

    class Config:
        from_attributes = True # Pydantic v2 replaces orm_mode

# Properties to return to client (the main schema for responses)
class InvoiceTemplate(InvoiceTemplateInDBBase):
    pass # Inherits all fields from InvoiceTemplateInDBBase

# Properties for a summary list of templates
class InvoiceTemplateSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_system_default: bool
    order_index: int

    class Config:
        from_attributes = True