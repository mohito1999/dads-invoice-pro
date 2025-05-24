from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from pydantic import HttpUrl # Ensure HttpUrl is imported

from app.models.item import Item as ItemModel # Alias
from app.schemas.item import ItemCreate, ItemUpdate

async def get_item(db: AsyncSession, item_id: uuid.UUID) -> ItemModel | None:
    """
    Get a single item by its ID.
    """
    result = await db.execute(select(ItemModel).filter(ItemModel.id == item_id))
    return result.scalars().first()

async def get_item_by_name_for_org(
    db: AsyncSession, *, name: str, organization_id: uuid.UUID
) -> ItemModel | None:
    """
    Get an item by name within a specific organization.
    """
    result = await db.execute(
        select(ItemModel)
        .filter(ItemModel.name == name)
        .filter(ItemModel.organization_id == organization_id)
    )
    return result.scalars().first()

async def get_items_by_organization(
    db: AsyncSession, *, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[ItemModel]:
    """
    Get a list of items for a specific organization with pagination.
    """
    result = await db.execute(
        select(ItemModel)
        .filter(ItemModel.organization_id == organization_id)
        .order_by(ItemModel.name) 
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_item(
    db: AsyncSession, *, item_in: ItemCreate
) -> ItemModel:
    """
    Create a new item.
    The organization_id must be provided in item_in.
    """
    print(f"\n--- DEBUG (crud_item.create_item): Creating item with payload: {item_in.model_dump()} ---")
    db_obj_data = item_in.model_dump(exclude_unset=True)

    # Convert HttpUrl to string if present for image_url
    if 'image_url' in db_obj_data and isinstance(db_obj_data.get('image_url'), HttpUrl): # Use .get for safety
        print(f"DEBUG (crud_item.create_item): Converting image_url from HttpUrl to str for create.")
        db_obj_data['image_url'] = str(db_obj_data['image_url'])
    
    db_obj = ItemModel(**db_obj_data) # Pass the modified dict
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    print(f"--- DEBUG (crud_item.create_item): Created item ID: {db_obj.id}, Image URL: {db_obj.image_url} ---\n")
    return db_obj

async def update_item(
    db: AsyncSession, *, db_obj: ItemModel, obj_in: ItemUpdate
) -> ItemModel:
    """
    Update an existing item.
    'db_obj' is the existing item model instance.
    'obj_in' is a Pydantic schema with the update data.
    """
    print(f"\n--- DEBUG (crud_item.update_item): Updating Item ID: {db_obj.id} ---")
    # obj_in is ItemUpdate, so image_url here can be HttpUrl if defined as such in ItemUpdate schema
    update_data = obj_in.model_dump(exclude_unset=True) 
    print(f"DEBUG (crud_item.update_item): update_data received (from obj_in.model_dump): {update_data}")

    # Optional: If name is being updated, check for duplicates within the same organization
    if "name" in update_data and update_data["name"] != db_obj.name:
        print(f"DEBUG (crud_item.update_item): Name change detected. Old: '{db_obj.name}', New: '{update_data['name']}'")
        existing_item = await get_item_by_name_for_org(
            db,
            name=update_data["name"],
            organization_id=db_obj.organization_id 
        )
        if existing_item and existing_item.id != db_obj.id:
            print(f"ERROR (crud_item.update_item): Attempt to update item name to an existing one ('{update_data['name']}') for org {db_obj.organization_id}. Name update potentially skipped or will cause DB error.")
            # Depending on DB constraints, this might raise an IntegrityError on commit.
            # For robust error handling, this check should be in the API endpoint to return HTTPException.
            # raise ValueError(f"Item name '{update_data['name']}' already exists in this organization.")

    print(f"DEBUG (crud_item.update_item): Current db_obj.image_url BEFORE applying updates: {db_obj.image_url}")
    
    # --- Start of the Fix Incorporation for HttpUrl in update_data ---
    # Prepare a dictionary of attributes to set on the db_obj
    # This dictionary will contain values converted to DB-compatible types (e.g., str for HttpUrl)
    processed_update_data = {}
    for field, value in update_data.items():
        if isinstance(value, HttpUrl): # Check if the value from Pydantic model dump is an HttpUrl instance
            print(f"DEBUG (crud_item.update_item): Converting field '{field}' (HttpUrl) to str: {str(value)}")
            processed_update_data[field] = str(value)
        else:
            processed_update_data[field] = value
    # --- End of the Fix Incorporation ---

    # Now apply the processed_update_data to the SQLAlchemy model instance
    for field, value_to_set in processed_update_data.items(): # Iterate over the processed dictionary
        print(f"DEBUG (crud_item.update_item): Setting field '{field}' to value '{value_to_set}' (type: {type(value_to_set)}) on Item ID {db_obj.id}")
        setattr(db_obj, field, value_to_set)
    
    # Log specific fields after setattr loop, before commit
    print(f"DEBUG (crud_item.update_item): db_obj.name AFTER loop: {db_obj.name}")
    print(f"DEBUG (crud_item.update_item): db_obj.description AFTER loop: {db_obj.description}")
    print(f"DEBUG (crud_item.update_item): db_obj.default_price AFTER loop: {db_obj.default_price}")
    print(f"DEBUG (crud_item.update_item): db_obj.default_unit AFTER loop: {db_obj.default_unit}")
    print(f"DEBUG (crud_item.update_item): db_obj.image_url AFTER setattr loop (BEFORE commit): {db_obj.image_url}")

    # db.add(db_obj) # Not strictly necessary if db_obj is already in session and modified,
                   # but doesn't hurt and ensures it's marked as dirty.
    await db.commit()
    print(f"DEBUG (crud_item.update_item): After db.commit() for Item ID: {db_obj.id}")
    
    await db.refresh(db_obj)
    print(f"DEBUG (crud_item.update_item): ItemModel db_obj.image_url AFTER db.refresh: {db_obj.image_url}")
    print(f"DEBUG (crud_item.update_item): All fields after refresh: name='{db_obj.name}', desc='{db_obj.description}', price='{db_obj.default_price}', unit='{db_obj.default_unit}', image_url='{db_obj.image_url}'")
    print(f"--- DEBUG (crud_item.update_item): Exiting for Item ID: {db_obj.id} ---\n")
    return db_obj

async def delete_item(db: AsyncSession, *, db_obj: ItemModel) -> ItemModel:
    """
    Delete an item.
    """
    print(f"\n--- DEBUG (crud_item.delete_item): Deleting Item ID: {db_obj.id}, Name: {db_obj.name} ---")
    await db.delete(db_obj)
    await db.commit()
    print(f"--- DEBUG (crud_item.delete_item): Deleted Item ID: {db_obj.id} ---\n")
    return db_obj