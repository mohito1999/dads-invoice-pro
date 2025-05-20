from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid

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
        .order_by(ItemModel.name) # Optional: order by name
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_item(
    db: AsyncSession, *, item_in: ItemCreate # organization_id is in ItemCreate
) -> ItemModel:
    """
    Create a new item.
    The organization_id must be provided in item_in.
    """
    db_obj_data = item_in.model_dump(exclude_unset=True)
    # organization_id is already part of db_obj_data from item_in
    db_obj = ItemModel(**db_obj_data)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_item(
    db: AsyncSession, *, db_obj: ItemModel, obj_in: ItemUpdate
) -> ItemModel:
    """
    Update an existing item.
    'db_obj' is the existing item model instance.
    'obj_in' is a Pydantic schema with the update data.
    """
    update_data = obj_in.model_dump(exclude_unset=True)

    # Optional: If name is being updated, check for duplicates within the same organization
    if "name" in update_data and update_data["name"] != db_obj.name:
        existing_item = await get_item_by_name_for_org(
            db,
            name=update_data["name"],
            organization_id=db_obj.organization_id # Check within the same org
        )
        if existing_item and existing_item.id != db_obj.id:
            # Handle this in the API layer with an HTTPException
            print(f"Attempt to update item name to an existing one for this org: {update_data['name']}")
            del update_data["name"] # Or raise ValueError

    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_item(db: AsyncSession, *, db_obj: ItemModel) -> ItemModel:
    """
    Delete an item.
    """
    # Consider implications: If item is used in past invoices, do we allow deletion?
    # Or mark as "archived"/"inactive"? For now, direct delete.
    await db.delete(db_obj)
    await db.commit()
    return db_obj