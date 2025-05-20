from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
import uuid
import shutil # For file operations (optional, if saving uploaded files)
from pathlib import Path # For path manipulation (optional)


from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps # Import deps to use the centralized dependency
from app.core.config import settings # If we need to define an upload directory

router = APIRouter()

# Local get_organization_from_id function is REMOVED from here.

@router.post("/", response_model=schemas.Item, status_code=status.HTTP_201_CREATED)
async def create_new_item(
    *,
    db: AsyncSession = Depends(get_db),
    item_in: schemas.ItemCreate, # Contains organization_id
    current_user: models.User = Depends(deps.get_current_active_user),
    # image: Optional[UploadFile] = File(None) # Optional image upload
) -> Any:
    """
    Create a new item for a specific organization owned by the current user.
    The 'organization_id' must be provided in the item_in payload.
    """
    # Authorize organization by calling the dependency function directly.
    organization = await deps.get_valid_organization_for_user(
        org_id=item_in.organization_id, db=db, current_user=current_user
    )

    existing_item = await crud.item.get_item_by_name_for_org(
        db, name=item_in.name, organization_id=organization.id
    )
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An item with this name already exists for this organization.",
        )
    
    # Handle image upload if provided - basic example
    # For a real app, consider cloud storage (S3, Azure Blob)
    # image_url_to_save = None
    # if image:
    #     # Define a path to save images, ensure it's configured and secure
    #     # This is a very basic local save, NOT production-ready.
    #     UPLOAD_DIR = Path("static/uploads/items") # Example, ensure this dir exists
    #     UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    #     file_extension = Path(image.filename).suffix
    #     # Generate a unique filename to avoid overwrites
    #     unique_filename = f"{uuid.uuid4()}{file_extension}"
    #     file_path = UPLOAD_DIR / unique_filename
    #     with open(file_path, "wb") as buffer:
    #         shutil.copyfileobj(image.file, buffer)
    #     # Construct a URL to access the image (depends on how you serve static files)
    #     # This would typically be settings.SERVER_HOST + /static/uploads/items/unique_filename
    #     image_url_to_save = f"/static/uploads/items/{unique_filename}" # Example
    #     # Update item_in or pass image_url_to_save to CRUD
    #     # item_in.image_url = image_url_to_save # If ItemCreate schema supports it
    #     # Or modify the db_obj_data in the CRUD function if passing directly


    # The item_in schema already includes organization_id
    item = await crud.item.create_item(db=db, item_in=item_in)
    # If image_url_to_save was generated and needs to be set on the item model directly:
    # if image_url_to_save and hasattr(item, 'image_url'):
    #    item.image_url = image_url_to_save
    #    db.add(item)
    #    await db.commit()
    #    await db.refresh(item)
    return item

@router.get("/", response_model=List[schemas.ItemSummary])
async def read_items_for_organization(
    *,
    db: AsyncSession = Depends(get_db),
    organization_id: uuid.UUID = Query(..., description="The ID of the organization to fetch items for"),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve items for a specific organization owned by the current user.
    """
    # Authorize organization by calling the dependency function directly.
    organization = await deps.get_valid_organization_for_user(
        org_id=organization_id, db=db, current_user=current_user
    )

    items = await crud.item.get_items_by_organization(
        db, organization_id=organization.id, skip=skip, limit=limit
    )
    return items

@router.get("/{item_id}", response_model=schemas.Item)
async def read_item_by_id(
    item_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific item by ID. Ensures the item belongs to an organization
    owned by the current user.
    """
    item = await crud.item.get_item(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Authorize: check if the item's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=item.organization_id, db=db, current_user=current_user
    )
    return item

@router.put("/{item_id}", response_model=schemas.Item)
async def update_existing_item(
    item_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    item_in: schemas.ItemUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
    # image: Optional[UploadFile] = File(None) # Optional image upload for update
) -> Any:
    """
    Update an item. Ensures the item belongs to an organization
    owned by the current user.
    """
    db_item = await crud.item.get_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Authorize: check if the item's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=db_item.organization_id, db=db, current_user=current_user
    )

    if item_in.name and item_in.name != db_item.name:
        existing_item = await crud.item.get_item_by_name_for_org(
            db, name=item_in.name, organization_id=db_item.organization_id
        )
        if existing_item and existing_item.id != item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another item with this name already exists for this organization.",
            )
    
    # Handle image update if provided (similar logic to create_new_item)
    # if image:
    #     ... save image, get new image_url_to_save ...
    #     # item_in should probably be a different schema for update if image is Form data
    #     # or handle image_url string directly in ItemUpdate schema
    #     # For now, assume item_in.image_url (if present in ItemUpdate) is a new URL string
    #     pass

    item = await crud.item.update_item(db=db, db_obj=db_item, obj_in=item_in)
    return item

@router.delete("/{item_id}", response_model=schemas.Item) # Or success message
async def delete_existing_item(
    item_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete an item. Ensures the item belongs to an organization
    owned by the current user.
    """
    db_item = await crud.item.get_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Authorize: check if the item's organization belongs to the current user
    # by calling the dependency function directly.
    await deps.get_valid_organization_for_user(
        org_id=db_item.organization_id, db=db, current_user=current_user
    )
        
    deleted_item = await crud.item.delete_item(db=db, db_obj=db_item)
    return deleted_item

# TODO: Add endpoint for uploading/updating item image specifically
# @router.post("/{item_id}/image", response_model=schemas.Item)
# async def upload_item_image(...): ...