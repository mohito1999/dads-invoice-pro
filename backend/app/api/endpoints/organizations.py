from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any # Any is used in return type hints
import uuid

from app import crud, schemas, models # Import models for type hinting
from app.db.session import get_db # Dependency to get a DB session
from app.api import deps # Import deps for authentication dependencies

router = APIRouter()

@router.post("/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_new_organization(
    *,
    db: AsyncSession = Depends(get_db),
    org_in: schemas.OrganizationCreate,
    current_user: models.User = Depends(deps.get_current_active_user) # Use dependency
) -> Any:
    """
    Create a new organization for the current authenticated user.
    """
    # Check if an organization with the same name already exists for this user
    existing_org = await crud.organization.get_organization_by_name_for_user(
        db, name=org_in.name, user_id=current_user.id
    )
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists for your account.",
        )
    
    organization = await crud.organization.create_organization( # Pass owner_id
        db=db, org_in=org_in, owner_id=current_user.id
    )
    return organization

@router.get("/", response_model=List[schemas.OrganizationSummary])
async def read_organizations_for_user( # Renamed for clarity
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user) # Use dependency
) -> Any:
    """
    Retrieve organizations for the current authenticated user.
    """
    organizations = await crud.organization.get_organizations_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return organizations

@router.get("/{org_id}", response_model=schemas.Organization)
async def read_organization_by_id(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user) # Use dependency
) -> Any:
    """
    Get a specific organization by ID, ensuring it belongs to the current user.
    """
    organization = await crud.organization.get_organization(db, org_id=org_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    if organization.user_id != current_user.id:
        # This check is crucial for authorization
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return organization

@router.put("/{org_id}", response_model=schemas.Organization)
async def update_existing_organization(
    org_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    org_in: schemas.OrganizationUpdate,
    current_user: models.User = Depends(deps.get_current_active_user) # Use dependency
) -> Any:
    """
    Update an organization, ensuring it belongs to the current user.
    """
    db_org = await crud.organization.get_organization(db, org_id=org_id)
    if not db_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    if db_org.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    organization = await crud.organization.update_organization(db=db, db_obj=db_org, obj_in=org_in)
    return organization

@router.delete("/{org_id}", response_model=schemas.Organization) # Or adjust response as needed
async def delete_existing_organization(
    org_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user) # Use dependency
) -> Any:
    """
    Delete an organization, ensuring it belongs to the current user.
    """
    db_org = await crud.organization.get_organization(db, org_id=org_id)
    if not db_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    if db_org.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # The deleted_organization variable holds the state of the object before deletion.
    deleted_organization = await crud.organization.delete_organization(db=db, db_obj=db_org)
    return deleted_organization
    # Consider returning status_code=204 with no content, or a simple success message:
    # return {"message": "Organization deleted successfully", "id": str(org_id)}