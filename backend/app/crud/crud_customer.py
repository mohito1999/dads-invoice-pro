from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_ # For combining filter conditions
import uuid

from app.models.customer import Customer as CustomerModel # Alias
from app.schemas.customer import CustomerCreate, CustomerUpdate

async def get_customer(db: AsyncSession, customer_id: uuid.UUID) -> CustomerModel | None:
    """
    Get a single customer by its ID.
    """
    result = await db.execute(select(CustomerModel).filter(CustomerModel.id == customer_id))
    return result.scalars().first()

async def get_customer_by_company_name_for_org(
    db: AsyncSession, *, company_name: str, organization_id: uuid.UUID
) -> CustomerModel | None:
    """
    Get a customer by company name within a specific organization.
    """
    result = await db.execute(
        select(CustomerModel)
        .filter(CustomerModel.company_name == company_name)
        .filter(CustomerModel.organization_id == organization_id)
    )
    return result.scalars().first()

async def get_customers_by_organization(
    db: AsyncSession, *, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[CustomerModel]:
    """
    Get a list of customers for a specific organization with pagination.
    """
    result = await db.execute(
        select(CustomerModel)
        .filter(CustomerModel.organization_id == organization_id)
        .order_by(CustomerModel.company_name) # Optional: order by name
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_customer(
    db: AsyncSession, *, customer_in: CustomerCreate # organization_id is in CustomerCreate
) -> CustomerModel:
    """
    Create a new customer.
    The organization_id must be provided in customer_in.
    """
    db_obj_data = customer_in.model_dump(exclude_unset=True)
    # organization_id is already part of db_obj_data from customer_in
    db_obj = CustomerModel(**db_obj_data)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_customer(
    db: AsyncSession, *, db_obj: CustomerModel, obj_in: CustomerUpdate
) -> CustomerModel:
    """
    Update an existing customer.
    'db_obj' is the existing customer model instance.
    'obj_in' is a Pydantic schema with the update data.
    """
    update_data = obj_in.model_dump(exclude_unset=True)

    # Optional: If company_name is being updated, check for duplicates within the same organization
    if "company_name" in update_data and update_data["company_name"] != db_obj.company_name:
        existing_customer = await get_customer_by_company_name_for_org(
            db,
            company_name=update_data["company_name"],
            organization_id=db_obj.organization_id # Check within the same org
        )
        if existing_customer and existing_customer.id != db_obj.id:
            # Handle this in the API layer with an HTTPException
            # For now, just print or skip update of this field
            print(f"Attempt to update company_name to an existing one for this org: {update_data['company_name']}")
            del update_data["company_name"] # Or raise ValueError

    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_customer(db: AsyncSession, *, db_obj: CustomerModel) -> CustomerModel:
    """
    Delete a customer.
    """
    await db.delete(db_obj)
    await db.commit()
    return db_obj