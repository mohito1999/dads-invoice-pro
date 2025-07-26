# backend/app/crud/crud_item.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # For eager loading
from sqlalchemy import func # For func.max
import uuid
from typing import List, Optional

from app.models.item import Item as ItemModel
from app.models.item_image import ItemImage as ItemImageModel
from app.schemas.item import ItemCreate, ItemUpdate # ItemImageCreate not directly used here for file uploads

async def get_item(db: AsyncSession, item_id: uuid.UUID) -> Optional[ItemModel]:
    print(f"DEBUG (crud.item.get_item): Fetching item ID {item_id} with image eager load.")
    result = await db.execute(
        select(ItemModel)
        .options(selectinload(ItemModel.images))
        .filter(ItemModel.id == item_id)
    )
    item = result.scalars().first()
    if item:
        print(f"DEBUG (crud.item.get_item): Fetched item. Name: {item.name}, Number of images loaded: {len(item.images) if item.images else 0}")
        if item.images:
            for idx, img_obj in enumerate(item.images):
                print(f"  Image {idx}: ID={img_obj.id}, URL={img_obj.image_url}, Order={img_obj.order_index}")
    else:
        print(f"DEBUG (crud.item.get_item): Item ID {item_id} not found.")
    return item


async def get_item_by_name_for_org(
    db: AsyncSession, *, name: str, organization_id: uuid.UUID
) -> Optional[ItemModel]:
    """
    Get an item by name within a specific organization.
    """
    result = await db.execute(
        select(ItemModel)
        .filter(ItemModel.name.ilike(name))
        .filter(ItemModel.organization_id == organization_id)
    )
    return result.scalars().first()

async def get_items_by_organization(
    db: AsyncSession, *, organization_id: uuid.UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
) -> List[ItemModel]:
    """
    Get a list of items for a specific organization, eagerly loading images.
    Optionally filters by search term in item name.
    """
    query = (
        select(ItemModel)
        .options(selectinload(ItemModel.images)) # Eager load images
        .filter(ItemModel.organization_id == organization_id)
    )
    if search:
        query = query.filter(ItemModel.name.ilike(f"%{search}%"))
    
    query = query.order_by(ItemModel.name).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    # Optional: If images are always needed in a specific order for all items
    # for item in items:
    #     if item.images:
    #         item.images.sort(key=lambda img: img.order_index)
    return items

async def create_item(
    db: AsyncSession, *, item_in: ItemCreate 
) -> ItemModel:
    """
    Create a new item. item_in no longer contains image_url directly.
    Images are handled by a separate upload endpoint and ItemImageModel.
    """
    print(f"\n--- DEBUG (crud_item.create_item): Creating item with payload: {item_in.model_dump()} ---")
    # image_url is removed from ItemCreate schema and ItemModel's direct attributes
    db_obj_data = item_in.model_dump(exclude_unset=True)
    db_obj = ItemModel(**db_obj_data)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    # Eager load images relationship, though it will be empty for a new item
    # This ensures the 'images' attribute is populated (as an empty list).
    await db.refresh(db_obj, attribute_names=['images']) 
    print(f"--- DEBUG (crud_item.create_item): Created item ID: {db_obj.id} (Images list will be empty initially) ---\n")
    return db_obj

async def update_item(
    db: AsyncSession, *, db_obj: ItemModel, obj_in: ItemUpdate
) -> ItemModel:
    """
    Update an existing item's non-image fields.
    Images are managed via separate endpoints and ItemImageModel.
    """
    print(f"\n--- DEBUG (crud_item.update_item): Updating Item ID: {db_obj.id} ---")
    # image_url is removed from ItemUpdate schema
    update_data = obj_in.model_dump(exclude_unset=True) 
    print(f"DEBUG (crud_item.update_item): update_data received: {update_data}")

    # If name is being updated, check for duplicates within the same organization
    if "name" in update_data and update_data["name"] != db_obj.name:
        print(f"DEBUG (crud_item.update_item): Name change detected. Old: '{db_obj.name}', New: '{update_data['name']}'")
        existing_item = await get_item_by_name_for_org(
            db,
            name=update_data["name"],
            organization_id=db_obj.organization_id 
        )
        if existing_item and existing_item.id != db_obj.id:
            print(f"ERROR (crud_item.update_item): Attempt to update item name to an existing one ('{update_data['name']}') for org {db_obj.organization_id}. Name update potentially skipped or will cause DB error.")
            # Consider raising an exception here to be caught by the API layer
            # e.g., raise ValueError(f"Item name '{update_data['name']}' already exists in this organization.")
            # For now, it just prints an error. The DB constraint might catch it.

    for field, value in update_data.items():
        # No HttpUrl conversion needed here as image_url is removed from ItemUpdate schema
        print(f"DEBUG (crud_item.update_item): Setting field '{field}' to value '{value}' (type: {type(value)}) on Item ID {db_obj.id}")
        setattr(db_obj, field, value)
    
    print(f"DEBUG (crud_item.update_item): All non-image fields after setattr loop (BEFORE commit): name='{db_obj.name}', desc='{db_obj.description}', price='{db_obj.default_price}', unit='{db_obj.default_unit}'")

    await db.commit()
    print(f"DEBUG (crud_item.update_item): After db.commit() for Item ID: {db_obj.id}")
    
    await db.refresh(db_obj)
    # Ensure the 'images' attribute is also refreshed/loaded, even if not directly modified by this function.
    await db.refresh(db_obj, attribute_names=['images']) 
    print(f"DEBUG (crud_item.update_item): All fields after refresh: name='{db_obj.name}', desc='{db_obj.description}', price='{db_obj.default_price}', unit='{db_obj.default_unit}'")
    print(f"--- DEBUG (crud_item.update_item): Exiting for Item ID: {db_obj.id} ---\n")
    return db_obj

async def delete_item(db: AsyncSession, *, db_obj: ItemModel) -> ItemModel:
    """
    Delete an item. Associated ItemImage records will be deleted by DB cascade 
    if the relationship is configured with "all, delete-orphan".
    Physical file deletion from storage needs to be handled separately (e.g., in the API endpoint or a background job).
    """
    print(f"\n--- DEBUG (crud_item.delete_item): Deleting Item ID: {db_obj.id}, Name: {db_obj.name} ---")
    # The actual file deletion from disk/S3 should be handled in the API endpoint
    # before or after this database operation.
    
    await db.delete(db_obj) # This should cascade to ItemImage records if relationship is set up with cascade="all, delete-orphan"
    await db.commit()
    print(f"--- DEBUG (crud_item.delete_item): Deleted Item (and its image records via cascade if configured) ID: {db_obj.id} ---\n")
    # db_obj is now detached and likely expired. Returning it might not be useful 
    # unless you capture its state before deletion for some reason.
    # For typical DELETE operations, often no object or a success status is returned from the CRUD layer.
    return db_obj 

# --- New CRUD functions for ItemImage ---
async def add_image_to_item(
    db: AsyncSession, *, item_id: uuid.UUID, image_url: str, order_index: Optional[int] = None, alt_text: Optional[str] = None
) -> ItemImageModel:
    """
    Adds an image record to an item.
    If order_index is None or not provided, it will be set to the next available index.
    """
    print(f"DEBUG (crud_item.add_image_to_item): Adding image '{image_url}' to item ID {item_id} with order {order_index}, alt_text: {alt_text}")
    
    final_order_index = order_index
    if final_order_index is None:
        current_max_order = await db.execute(
            select(func.max(ItemImageModel.order_index)).filter(ItemImageModel.item_id == item_id)
        )
        max_idx = current_max_order.scalar_one_or_none()
        final_order_index = (max_idx + 1) if max_idx is not None else 0
        print(f"DEBUG (crud_item.add_image_to_item): Auto-calculated order_index: {final_order_index}")

    db_image = ItemImageModel(
        item_id=item_id, 
        image_url=image_url, 
        order_index=final_order_index,
        alt_text=alt_text
    )
    db.add(db_image)
    await db.commit()
    await db.refresh(db_image)
    print(f"DEBUG (crud_item.add_image_to_item): Added image record ID {db_image.id}, URL: {db_image.image_url}, Order: {db_image.order_index}")
    return db_image

async def get_item_image(db: AsyncSession, image_id: uuid.UUID) -> Optional[ItemImageModel]:
    """
    Get a single item image by its ID.
    """
    print(f"DEBUG (crud_item.get_item_image): Fetching ItemImage record ID: {image_id}")
    result = await db.execute(select(ItemImageModel).filter(ItemImageModel.id == image_id))
    image = result.scalars().first()
    if image:
        print(f"DEBUG (crud_item.get_item_image): Found ItemImage: {image.id}, URL: {image.image_url}")
    else:
        print(f"DEBUG (crud_item.get_item_image): ItemImage record ID: {image_id} not found.")
    return image

async def delete_item_image_record(db: AsyncSession, image_id: uuid.UUID) -> Optional[ItemImageModel]:
    """
    Delete an ItemImage record from the database.
    Physical file deletion from storage needs to be handled separately.
    """
    db_image = await get_item_image(db, image_id=image_id) # Reuse get_item_image
    if db_image:
        print(f"DEBUG (crud_item.delete_item_image_record): Deleting ItemImage record ID: {db_image.id}, URL: {db_image.image_url}")
        # Physical file deletion should be handled in the API endpoint.
        await db.delete(db_image)
        await db.commit()
        print(f"DEBUG (crud_item.delete_item_image_record): Deleted ItemImage record from DB.")
        return db_image # Return the (now deleted) object state before deletion
    else:
        print(f"DEBUG (crud_item.delete_item_image_record): ItemImage record ID: {image_id} not found for deletion.")
        return None