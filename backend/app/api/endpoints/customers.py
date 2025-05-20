from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any # Any is used in return type hints
import uuid

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps # deps is imported to use get_valid_organization_for_user

router = APIRouter()

# Local get_organization_from_id function is REMOVED from here.

@router.post("/", response_model=schemas.Customer, status_code=status.HTTP_201_CREATED)
async def create_new_customer(
    *,
    db: AsyncSession = Depends(get_db),
    customer_in: schemas.CustomerCreate, # Contains organization_id
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create a new customer for a specific organization owned by the current user.
    The 'organization_id' must be provided in the customer_in payload.
    """
    # Authorize that the current user owns the target organization
    # by calling the dependency function directly.
    organization = await deps.get_valid_organization_for_user(
        org_id=customer_in.organization_id, db=db, current_user=current_user
    )
    # organization is now validated and belongs to current_user

    # Check if customer with the same company name already exists for this organization
    existing_customer = await crud.customer.get_customer_by_company_name_for_org(
        db, company_name=customer_in.company_name, organization_id=organization.id
    )
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer with this company name already exists for this organization.",
        )
    
    # The customer_in schema already includes organization_id, so CRUD function will use it.
    customer = await crud.customer.create_customer(db=db, customer_in=customer_in)
    return customer

@router.get("/", response_model=List[schemas.CustomerSummary])
async def read_customers_for_organization(
    *,
    db: AsyncSession = Depends(get_db),
    organization_id: uuid.UUID = Query(..., description="The ID of the organization to fetch customers for"),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve customers for a specific organization owned by the current user.
    """
    # Authorize organization by calling the dependency function directly.
    organization = await deps.get_valid_organization_for_user(
        org_id=organization_id, db=db, current_user=current_user
    )

    customers = await crud.customer.get_customers_by_organization(
        db, organization_id=organization.id, skip=skip, limit=limit
    )
    return customers

@router.get("/{customer_id}", response_model=schemas.Customer)
async def read_customer_by_id(
    customer_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific customer by ID. Ensures the customer belongs to an organization
    owned by the current user.
    """
    customer = await crud.customer.get_customer(db, customer_id=customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    # Authorize: check if the customer's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=customer.organization_id, db=db, current_user=current_user
    )
    # If the above didn't raise an exception, user is authorized for this customer's org.

    return customer

@router.put("/{customer_id}", response_model=schemas.Customer)
async def update_existing_customer(
    customer_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    customer_in: schemas.CustomerUpdate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update a customer. Ensures the customer belongs to an organization
    owned by the current user.
    """
    db_customer = await crud.customer.get_customer(db, customer_id=customer_id)
    if not db_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Authorize: check if the customer's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=db_customer.organization_id, db=db, current_user=current_user
    )

    # Check for duplicate company name if it's being changed
    if customer_in.company_name and customer_in.company_name != db_customer.company_name:
        existing_customer = await crud.customer.get_customer_by_company_name_for_org(
            db, company_name=customer_in.company_name, organization_id=db_customer.organization_id
        )
        if existing_customer and existing_customer.id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another customer with this company name already exists for this organization.",
            )

    customer = await crud.customer.update_customer(db=db, db_obj=db_customer, obj_in=customer_in)
    return customer

@router.delete("/{customer_id}", response_model=schemas.Customer)
async def delete_existing_customer(
    customer_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete a customer. Ensures the customer belongs to an organization
    owned by the current user.
    """
    db_customer = await crud.customer.get_customer(db, customer_id=customer_id)
    if not db_customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Authorize: check if the customer's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=db_customer.organization_id, db=db, current_user=current_user
    )
        
    deleted_customer = await crud.customer.delete_customer(db=db, db_obj=db_customer)
    return deleted_customer