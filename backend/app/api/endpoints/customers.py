# backend/app/api/endpoints/customers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any 
import uuid

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.Customer, status_code=status.HTTP_201_CREATED)
async def create_new_customer(
    *,
    db: AsyncSession = Depends(get_db),
    customer_in: schemas.CustomerCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create a new customer for a specific organization owned by the current user.
    """
    organization = await deps.get_valid_organization_for_user(
        db=db, org_id=customer_in.organization_id, current_user=current_user
    )

    existing_customer = await crud.customer.get_customer_by_company_name_for_org(
        db, company_name=customer_in.company_name, organization_id=organization.id
    )
    if existing_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer with this company name already exists for this organization.",
        )
    
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
    organization = await deps.get_valid_organization_for_user(
        db=db, org_id=organization_id, current_user=current_user
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
    
    await deps.get_valid_organization_for_user(
        db=db, org_id=customer.organization_id, current_user=current_user
    )
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

    await deps.get_valid_organization_for_user(
        db=db, org_id=db_customer.organization_id, current_user=current_user
    )

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

    await deps.get_valid_organization_for_user(
        db=db, org_id=db_customer.organization_id, current_user=current_user
    )
        
    deleted_customer = await crud.customer.delete_customer(db=db, db_obj=db_customer)
    return deleted_customer