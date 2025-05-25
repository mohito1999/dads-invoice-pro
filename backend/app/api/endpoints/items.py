# backend/app/api/endpoints/items.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
import uuid
import shutil
from pathlib import Path
from sqlalchemy import func, select

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps

APP_DIR_FROM_ENDPOINTS_ITEMS = Path(__file__).resolve().parent.parent.parent
STATIC_UPLOADS_DIR_ITEMS = APP_DIR_FROM_ENDPOINTS_ITEMS.parent / "static" / "uploads"
ITEM_IMAGES_SUBDIR = "item_images"

router = APIRouter()

@router.post("/", response_model=schemas.Item, status_code=status.HTTP_201_CREATED)
async def create_new_item(
    item_in: schemas.ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    await deps.get_valid_organization_for_user(
        db=db, org_id=item_in.organization_id, current_user=current_user
    )
    existing_item = await crud.item.get_item_by_name_for_org(db, name=item_in.name, organization_id=item_in.organization_id)
    if existing_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An item with this name already exists in this organization.")
    item = await crud.item.create_item(db=db, item_in=item_in)
    return item

@router.get("/", response_model=List[schemas.ItemSummary])
async def read_items_for_organization(
    organization_id: uuid.UUID = Query(..., description="The ID of the organization to fetch items for"),
    search: Optional[str] = Query(None, description="Search term to filter items by name"),
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=200), # Frontend must respect this limit
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    await deps.get_valid_organization_for_user(
        db=db, org_id=organization_id, current_user=current_user
    )
    items_from_db = await crud.item.get_items_by_organization(
        db, organization_id=organization_id, search=search, skip=skip, limit=limit
    )
    item_summaries = []
    for item_model in items_from_db:
        primary_img_url = None
        # Ensure images are sorted by order_index if you want the first to be specific
        # The relationship in Item model already has order_by="ItemImage.order_index"
        if item_model.images and len(item_model.images) > 0: 
            primary_img_url = item_model.images[0].image_url
        
        item_summaries.append(
            schemas.ItemSummary(
                id=item_model.id,
                name=item_model.name,
                description=item_model.description, # <-- ENSURE THIS IS PASSED
                default_price=item_model.default_price,
                default_unit=item_model.default_unit,
                primary_image_url=primary_img_url
            )
        )
    return item_summaries

@router.get("/{item_id}", response_model=schemas.Item)
async def read_item_by_id(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    item = await crud.item.get_item(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await deps.get_valid_organization_for_user(
        db=db, org_id=item.organization_id, current_user=current_user
    )
    return item

@router.put("/{item_id}", response_model=schemas.Item)
async def update_existing_item(
    item_id: uuid.UUID,
    item_in: schemas.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    db_item = await crud.item.get_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await deps.get_valid_organization_for_user(
        db=db, org_id=db_item.organization_id, current_user=current_user
    )
    if item_in.name is not None and item_in.name != db_item.name:
         existing_item_with_new_name = await crud.item.get_item_by_name_for_org(
             db, name=item_in.name, organization_id=db_item.organization_id
         )
         if existing_item_with_new_name and existing_item_with_new_name.id != item_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Another item with this name already exists in this organization.")
    item = await crud.item.update_item(db=db, db_obj=db_item, obj_in=item_in)
    return item

@router.delete("/{item_id}", response_model=schemas.Item) 
async def delete_existing_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    db_item = await crud.item.get_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await deps.get_valid_organization_for_user(
        db=db, org_id=db_item.organization_id, current_user=current_user
    )
    if db_item.images:
        for image_record in db_item.images:
            if image_record.image_url and image_record.image_url.startswith("/static/"):
                relative_path = image_record.image_url[len("/static/"):] 
                file_to_delete_on_server = STATIC_UPLOADS_DIR_ITEMS.parent / relative_path
                try:
                    if file_to_delete_on_server.is_file():
                        file_to_delete_on_server.unlink()
                except Exception as e_del:
                    print(f"ERROR deleting item image file {file_to_delete_on_server}: {e_del}")
    deleted_item_data = await crud.item.delete_item(db=db, db_obj=db_item)
    return deleted_item_data

@router.post("/{item_id}/images", response_model=schemas.Item, status_code=status.HTTP_201_CREATED)
async def upload_item_images_endpoint(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    files: List[UploadFile] = File(...)
) -> Any:
    db_item = await crud.item.get_item(db, item_id=item_id) # This get_item should eager load existing images
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await deps.get_valid_organization_for_user(
        db=db, org_id=db_item.organization_id, current_user=current_user
    )
    item_specific_image_storage_path = STATIC_UPLOADS_DIR_ITEMS / ITEM_IMAGES_SUBDIR / str(item_id)
    item_specific_image_storage_path.mkdir(parents=True, exist_ok=True)
    
    # Determine the starting order_index for new images
    # The relationship `ItemModel.images` is already ordered by `order_index` due to `lazy="selectin"` and `order_by`
    next_order_index = 0
    if db_item.images and len(db_item.images) > 0:
        next_order_index = db_item.images[-1].order_index + 1


    for file_upload in files:
        allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"]
        if file_upload.content_type not in allowed_mime_types:
            # Consider collecting errors to return to user
            print(f"Skipping file {file_upload.filename} due to invalid MIME type: {file_upload.content_type}")
            continue 
        try:
            file_extension = Path(file_upload.filename if file_upload.filename else ".png").suffix.lower()
            if not file_extension: file_extension = ".png"
            unique_filename_for_disk = f"{uuid.uuid4()}{file_extension}"
            file_location_on_server = item_specific_image_storage_path / unique_filename_for_disk
            
            with open(file_location_on_server, "wb+") as file_object:
                shutil.copyfileobj(file_upload.file, file_object)
                
            image_url_for_db = f"/static/uploads/{ITEM_IMAGES_SUBDIR}/{item_id}/{unique_filename_for_disk}"
            
            await crud.item.add_image_to_item(
                db=db, 
                item_id=item_id, 
                image_url=image_url_for_db, 
                order_index=next_order_index, # Pass the calculated order_index
                alt_text=Path(file_upload.filename if file_upload.filename else "item image").stem
            )
            next_order_index += 1
        except Exception as e:
            print(f"Error processing image file {file_upload.filename}: {e}")
            # Consider removing the saved file if DB entry fails
            if 'file_location_on_server' in locals() and file_location_on_server.exists():
                try:
                    file_location_on_server.unlink()
                except Exception as e_del_file:
                    print(f"Error cleaning up partially saved file {file_location_on_server}: {e_del_file}")
        finally:
            file_upload.file.close()
            
    # Re-fetch the item to ensure the response includes all images (old and newly added)
    # and they are correctly ordered
    updated_item_with_images = await crud.item.get_item(db, item_id=item_id)
    if not updated_item_with_images:
         # This should ideally not happen if the item existed.
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve item after image uploads.")
    return updated_item_with_images

@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_single_item_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    image_record = await crud.item.get_item_image(db, image_id=image_id)
    if not image_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record not found")
    
    parent_item = await crud.item.get_item(db, item_id=image_record.item_id) # Fetch parent to check auth
    if not parent_item: 
        print(f"Warning: Parent item for image ID {image_id} (item_id {image_record.item_id}) not found, but deleting image record.")
        # If parent item is gone, user auth cannot be checked against it. 
        # Depending on policy, you might allow deletion or forbid if parent is gone.
        # For now, if parent_item is None, the auth check below will be skipped.
    else:
        await deps.get_valid_organization_for_user(
            db=db, org_id=parent_item.organization_id, current_user=current_user
        )

    if image_record.image_url and image_record.image_url.startswith("/static/"):
        relative_path_from_static_root = image_record.image_url[len("/static/"):]
        static_dir_base = STATIC_UPLOADS_DIR_ITEMS.parent
        file_to_delete_on_server = static_dir_base / relative_path_from_static_root
        try:
            if file_to_delete_on_server.is_file():
                file_to_delete_on_server.unlink()
        except Exception as e_del:
            print(f"ERROR deleting physical image file {file_to_delete_on_server}: {e_del}")
            # Decide if this is critical. For now, log and proceed.
            
    await crud.item.delete_item_image_record(db, image_id=image_id)
    return None # For 204 No Content