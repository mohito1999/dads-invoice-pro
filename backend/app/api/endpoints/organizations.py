# backend/app/api/endpoints/organizations.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any # Any is used in return type hints
import uuid
import shutil
from pathlib import Path

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps

# Path construction logic
# Assuming this file is backend/app/api/endpoints/organizations.py
# APP_DIR_FROM_ENDPOINTS will point to backend/app/
APP_DIR_FROM_ENDPOINTS = Path(__file__).resolve().parent.parent.parent
STATIC_UPLOADS_DIR = APP_DIR_FROM_ENDPOINTS.parent / "static" / "uploads"
ORG_LOGO_SUBDIR = "org_logos"

router = APIRouter()

@router.post("/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_new_organization(
    *,
    db: AsyncSession = Depends(get_db),
    org_in: schemas.OrganizationCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create a new organization for the current authenticated user.
    """
    existing_org = await crud.organization.get_organization_by_name_for_user(
        db, name=org_in.name, user_id=current_user.id
    )
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists for your account.",
        )
    
    organization = await crud.organization.create_organization(
        db=db, org_in=org_in, owner_id=current_user.id
    )
    return organization

@router.get("/", response_model=List[schemas.OrganizationSummary])
async def read_organizations_for_user(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
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
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific organization by ID, ensuring it belongs to the current user.
    """
    organization = await deps.get_valid_organization_for_user(
        db=db, org_id=org_id, current_user=current_user
    )
    return organization


@router.put("/{org_id}", response_model=schemas.Organization)
async def update_existing_organization(
    org_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    org_in: schemas.OrganizationUpdate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update an organization, ensuring it belongs to the current user.
    """
    db_org = await deps.get_valid_organization_for_user(
        db=db, org_id=org_id, current_user=current_user
    )
    organization = await crud.organization.update_organization(db=db, db_obj=db_org, obj_in=org_in)
    return organization

@router.delete("/{org_id}", response_model=schemas.Organization)
async def delete_existing_organization(
    org_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete an organization, ensuring it belongs to the current user.
    """
    db_org = await deps.get_valid_organization_for_user(
        db=db, org_id=org_id, current_user=current_user
    )

    deleted_organization = await crud.organization.delete_organization(db=db, db_obj=db_org)
    if deleted_organization and deleted_organization.logo_url:
        try:
            logo_filename = Path(deleted_organization.logo_url).name
            logo_path_on_server = STATIC_UPLOADS_DIR / ORG_LOGO_SUBDIR / logo_filename
            if logo_path_on_server.exists():
                logo_path_on_server.unlink()
                print(f"Deleted logo file: {logo_path_on_server}")
        except Exception as e:
            print(f"Error deleting logo file {deleted_organization.logo_url} for org {org_id}: {e}")

    return deleted_organization


@router.post("/{org_id}/upload-logo", response_model=schemas.Organization)
async def upload_organization_logo(
    org_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    logo_file: UploadFile = File(...)
) -> Any:
    """
    Upload or replace an organization's logo.
    """
    db_org = await deps.get_valid_organization_for_user(
        db=db, org_id=org_id, current_user=current_user
    )

    allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "image/svg+xml", "image/webp"]
    if logo_file.content_type not in allowed_mime_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image type. Allowed types: JPEG, PNG, GIF, SVG, WebP.")

    organization_logos_path = STATIC_UPLOADS_DIR / ORG_LOGO_SUBDIR
    organization_logos_path.mkdir(parents=True, exist_ok=True)

    file_extension = Path(logo_file.filename if logo_file.filename else "logo.png").suffix.lower()
    if not file_extension: 
        file_extension = ".png"
        
    filename = f"{db_org.id}{file_extension}"
    file_location_on_server = organization_logos_path / filename

    if db_org.logo_url:
        old_logo_filename = Path(db_org.logo_url).name
        if old_logo_filename != filename: 
            old_file_path_on_server = organization_logos_path / old_logo_filename
            if old_file_path_on_server.exists():
                try:
                    old_file_path_on_server.unlink()
                    print(f"Deleted old logo: {old_file_path_on_server}")
                except Exception as e_del:
                    print(f"Error deleting old logo {old_file_path_on_server}: {e_del}")

    try:
        with open(file_location_on_server, "wb+") as file_object:
            shutil.copyfileobj(logo_file.file, file_object)
    except Exception as e:
        print(f"Error saving logo file {file_location_on_server}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save logo file.")
    finally:
        logo_file.file.close() 

    logo_url_path_for_db = f"/static/uploads/{ORG_LOGO_SUBDIR}/{filename}"
    
    db_org.logo_url = logo_url_path_for_db
    await db.commit()
    await db.refresh(db_org)
    
    return db_org