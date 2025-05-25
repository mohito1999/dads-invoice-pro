# backend/app/api/endpoints/invoice_templates.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
import uuid

from app import crud, models, schemas # models for type hint, schemas for validation/response
from app.db.session import get_db
from app.api import deps # For get_current_active_user (and potentially admin later)

router = APIRouter()

@router.post("/", response_model=schemas.InvoiceTemplate, status_code=status.HTTP_201_CREATED)
async def create_new_invoice_template(
    *,
    db: AsyncSession = Depends(get_db),
    template_in: schemas.InvoiceTemplateCreate,
    # For now, any authenticated user can create. Consider restricting to admin later.
    current_user: models.User = Depends(deps.get_current_active_user) 
) -> Any:
    """
    Create a new invoice template.
    (Currently accessible by any authenticated user. Could be restricted to admin.)
    """
    existing_template_name = await crud.invoice_template.get_invoice_template_by_name(db, name=template_in.name)
    if existing_template_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invoice template with this name already exists.",
        )
    
    existing_template_path = await crud.invoice_template.get_invoice_template_by_path(db, file_path=template_in.template_file_path)
    if existing_template_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invoice template with this file path already exists.",
        )
        
    template = await crud.invoice_template.create_invoice_template(db=db, template_in=template_in)
    return template

@router.get("/", response_model=List[schemas.InvoiceTemplateSummary])
async def read_all_invoice_templates(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: models.User = Depends(deps.get_current_active_user) # Ensure user is authenticated
) -> Any:
    """
    Retrieve all invoice templates.
    """
    templates = await crud.invoice_template.get_all_invoice_templates(db, skip=skip, limit=limit)
    # Convert to summary schema if needed, or ensure InvoiceTemplate can be directly used.
    # For consistency with other list endpoints, returning summary is good practice.
    return [
        schemas.InvoiceTemplateSummary.model_validate(template) for template in templates
    ]


@router.get("/{template_id}", response_model=schemas.InvoiceTemplate)
async def read_invoice_template_by_id(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user) # Ensure user is authenticated
) -> Any:
    """
    Get a specific invoice template by ID.
    """
    template = await crud.invoice_template.get_invoice_template(db, template_id=template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")
    return template

@router.put("/{template_id}", response_model=schemas.InvoiceTemplate)
async def update_existing_invoice_template(
    template_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    template_in: schemas.InvoiceTemplateUpdate,
    current_user: models.User = Depends(deps.get_current_active_user) # Admin/permission check later
) -> Any:
    """
    Update an invoice template.
    (Currently accessible by any authenticated user. Could be restricted to admin.)
    """
    db_template = await crud.invoice_template.get_invoice_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")

    # Check for name conflict if name is being changed
    if template_in.name and template_in.name != db_template.name:
        existing_template_name = await crud.invoice_template.get_invoice_template_by_name(db, name=template_in.name)
        if existing_template_name and existing_template_name.id != template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invoice template with this name already exists.",
            )

    # Check for file path conflict if path is being changed
    if template_in.template_file_path and template_in.template_file_path != db_template.template_file_path:
        existing_template_path = await crud.invoice_template.get_invoice_template_by_path(db, file_path=template_in.template_file_path)
        if existing_template_path and existing_template_path.id != template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invoice template with this file path already exists.",
            )
            
    template = await crud.invoice_template.update_invoice_template(db=db, db_obj=db_template, obj_in=template_in)
    return template

@router.delete("/{template_id}", response_model=schemas.InvoiceTemplate) # Or return status 204 No Content
async def delete_existing_invoice_template(
    template_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user) # Admin/permission check later
) -> Any:
    """
    Delete an invoice template.
    (Currently accessible by any authenticated user. Could be restricted to admin.)
    """
    db_template = await crud.invoice_template.get_invoice_template(db, template_id=template_id)
    if not db_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice template not found")
    
    try:
        deleted_template = await crud.invoice_template.delete_invoice_template(db=db, db_obj=db_template)
        return deleted_template # Returns the deleted object data
    except ValueError as e: # Catch specific error from CRUD for default template deletion
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Generic error for other unexpected issues
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete invoice template.")