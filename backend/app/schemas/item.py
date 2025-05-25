# backend/app/schemas/item.py
from pydantic import BaseModel, HttpUrl, constr, Field # HttpUrl might not be needed if storing relative paths
from typing import Optional, List
import uuid

class ItemImageBase(BaseModel):
    image_url: str # Relative path like /static/uploads/item_images/item_id/filename.jpg
    order_index: Optional[int] = 0
    alt_text: Optional[str] = None

class ItemImageCreate(ItemImageBase): # For internal use or specific endpoint
    item_id: uuid.UUID

class ItemImage(ItemImageBase): # Response schema for an image
    id: uuid.UUID
    alt_text: Optional[str] = None
    class Config:
        from_attributes = True

class ItemBase(BaseModel):
    name: constr(min_length=1, max_length=255)
    description: Optional[str] = None
    default_price: Optional[float] = Field(default=None, ge=0) # Allow 0 for items like packing materials
    default_unit: Optional[str] = None
    # image_url was removed from here

class ItemCreate(ItemBase):
    organization_id: uuid.UUID
    # Images are uploaded via a separate endpoint after item creation or during item update

class ItemUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=255)] = None
    description: Optional[str] = None
    default_price: Optional[float] = Field(default=None, ge=0, allow_none=True)
    default_unit: Optional[str] = None
    # Images are managed via separate endpoints

class Item(ItemBase): # Full Item response schema
    id: uuid.UUID
    organization_id: uuid.UUID
    images: List[ItemImage] = [] # List of associated images

    class Config:
        from_attributes = True

class ItemSummary(BaseModel): # For lists
    id: uuid.UUID
    name: str
    description: Optional[str] = None 
    default_price: Optional[float] = None
    default_unit: Optional[str] = None
    primary_image_url: Optional[str] = None # Will be the URL of the first image (e.g., lowest order_index)

    class Config:
        from_attributes = True