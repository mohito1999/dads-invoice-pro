from pydantic import BaseModel, HttpUrl, constr, Field
from typing import Optional, List
import uuid

# Shared properties for an item
class ItemBase(BaseModel):
    name: constr(min_length=1, max_length=255)
    description: Optional[str] = None
    default_price: Optional[float] = Field(default=None, gt=0) # Price must be greater than 0 if set
    default_unit: Optional[str] = None # e.g., "piece", "carton", "kg", "set"
    # default_currency: Optional[str] = None # We'll handle currency at the invoice_item level for more flexibility

# Properties to receive on item creation
class ItemCreate(ItemBase):
    organization_id: uuid.UUID # Item must belong to an organization
    # image_urls: Optional[List[HttpUrl]] = [] # For multiple image URLs

# Properties to receive on item update
class ItemUpdate(BaseModel): # All fields optional for update
    name: Optional[constr(min_length=1, max_length=255)] = None
    description: Optional[str] = None
    default_price: Optional[float] = Field(default=None, gt=0, allow_none=True) # Allow explicitly setting to None
    default_unit: Optional[str] = None
    image_url: Optional[HttpUrl] = None

# Properties stored in DB
class ItemInDBBase(ItemBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    # We will handle images separately, perhaps as a list of URLs or a related table
    # For simplicity now, let's assume a primary image URL on the item itself,
    # and we can expand later if multiple images per item are stored directly.
    # Or, we can have a separate Image model linked to Item.
    # Let's start with a single image_url for now.
    image_url: Optional[HttpUrl] = None # Placeholder for a primary image

    class Config:
        from_attributes = True

# Properties to return to client
class Item(ItemInDBBase):
    pass

# Summary for lists/dropdowns
class ItemSummary(BaseModel):
    id: uuid.UUID
    name: str
    default_price: Optional[float] = None
    default_unit: Optional[str] = None
    image_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True