from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
# from sqlalchemy.orm import selectinload # For eager loading related data if needed later
import uuid

from app.models.organization import Organization as OrganizationModel
from app.models.user import User as UserModel # Import User model
from app.schemas.organization import OrganizationCreate, OrganizationUpdate

async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> OrganizationModel | None:
    """
    Get a single organization by its ID.
    """
    result = await db.execute(select(OrganizationModel).filter(OrganizationModel.id == org_id))
    return result.scalars().first()

async def get_organization_by_name_for_user(db: AsyncSession, name: str, user_id: uuid.UUID) -> OrganizationModel | None:
    """
    Get a single organization by its name for a specific user.
    """
    result = await db.execute(
        select(OrganizationModel)
        .filter(OrganizationModel.name == name)
        .filter(OrganizationModel.user_id == user_id)
    )
    return result.scalars().first()

async def get_organizations_by_user(db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[OrganizationModel]:
    """
    Get a list of organizations for a specific user with pagination.
    """
    result = await db.execute(
        select(OrganizationModel)
        .filter(OrganizationModel.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_organization(
    db: AsyncSession, *, org_in: OrganizationCreate, owner_id: uuid.UUID # <--- ADDED owner_id
) -> OrganizationModel:
    """
    Create a new organization for a specific owner.
    """
    # Pydantic v2: db_obj_data = org_in.model_dump(exclude_unset=True)
    # Pydantic v1: db_obj_data = org_in.dict(exclude_unset=True)
    db_obj_data = org_in.model_dump(exclude_unset=True)
    db_obj = OrganizationModel(**db_obj_data, user_id=owner_id) # <--- SET user_id here

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_organization(
    db: AsyncSession, *, db_obj: OrganizationModel, obj_in: OrganizationUpdate
) -> OrganizationModel:
    """
    Update an existing organization.
    'db_obj' is the existing organization model instance from the database.
    'obj_in' is a Pydantic schema with the update data.
    """
    # Pydantic v2: update_data = obj_in.model_dump(exclude_unset=True)
    # Pydantic v1: update_data = obj_in.dict(exclude_unset=True)
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj) # or await db.merge(db_obj) if db_obj could be detached
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_organization(db: AsyncSession, *, db_obj: OrganizationModel) -> OrganizationModel:
    """
    Delete an organization.
    """
    await db.delete(db_obj)
    await db.commit()
    # After deletion, the object is no longer in the session.
    # Returning the object as it was before deletion for confirmation.
    return db_obj