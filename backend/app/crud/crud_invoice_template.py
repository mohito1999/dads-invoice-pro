# backend/app/crud/crud_invoice_template.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update as sqlalchemy_update
import uuid
from typing import List, Optional

from app.models.invoice_template import InvoiceTemplate as InvoiceTemplateModel
from app.schemas.invoice_template import InvoiceTemplateCreate, InvoiceTemplateUpdate

async def get_invoice_template(db: AsyncSession, template_id: uuid.UUID) -> Optional[InvoiceTemplateModel]:
    """
    Get a single invoice template by its ID.
    """
    result = await db.execute(select(InvoiceTemplateModel).filter(InvoiceTemplateModel.id == template_id))
    return result.scalars().first()

async def get_invoice_template_by_name(db: AsyncSession, name: str) -> Optional[InvoiceTemplateModel]:
    """
    Get a single invoice template by its name.
    """
    result = await db.execute(select(InvoiceTemplateModel).filter(InvoiceTemplateModel.name == name))
    return result.scalars().first()

async def get_invoice_template_by_path(db: AsyncSession, file_path: str) -> Optional[InvoiceTemplateModel]:
    """
    Get a single invoice template by its file path.
    """
    result = await db.execute(select(InvoiceTemplateModel).filter(InvoiceTemplateModel.template_file_path == file_path))
    return result.scalars().first()

async def get_system_default_template(db: AsyncSession) -> Optional[InvoiceTemplateModel]:
    """
    Get the system default invoice template.
    """
    result = await db.execute(select(InvoiceTemplateModel).filter(InvoiceTemplateModel.is_system_default == True))
    return result.scalars().first()

async def get_all_invoice_templates(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[InvoiceTemplateModel]:
    """
    Get a list of all invoice templates with pagination, ordered by order_index then name.
    """
    result = await db.execute(
        select(InvoiceTemplateModel)
        .order_by(InvoiceTemplateModel.order_index, InvoiceTemplateModel.name)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_invoice_template(db: AsyncSession, *, template_in: InvoiceTemplateCreate) -> InvoiceTemplateModel:
    """
    Create a new invoice template.
    If template_in.is_system_default is True, it ensures any other existing default is unset.
    """
    if template_in.is_system_default:
        # Unset any other system default template
        await db.execute(
            sqlalchemy_update(InvoiceTemplateModel)
            .where(InvoiceTemplateModel.is_system_default == True)
            .values(is_system_default=False)
        )

    db_obj_data = template_in.model_dump(exclude_unset=True)
    db_obj = InvoiceTemplateModel(**db_obj_data)
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_invoice_template(
    db: AsyncSession, *, db_obj: InvoiceTemplateModel, obj_in: InvoiceTemplateUpdate
) -> InvoiceTemplateModel:
    """
    Update an existing invoice template.
    If obj_in.is_system_default is True, it ensures any other existing default is unset.
    """
    update_data = obj_in.model_dump(exclude_unset=True)

    if update_data.get("is_system_default") is True and not db_obj.is_system_default:
        # If setting this template as default, unset any other default
        await db.execute(
            sqlalchemy_update(InvoiceTemplateModel)
            .where(InvoiceTemplateModel.id != db_obj.id) # Don't unset itself
            .where(InvoiceTemplateModel.is_system_default == True)
            .values(is_system_default=False)
        )
    
    # Prevent unsetting the only system default directly through update if it's the only one
    # (This logic might be better placed in an API layer or service layer)
    if update_data.get("is_system_default") is False and db_obj.is_system_default:
        count_query = select(func.count(InvoiceTemplateModel.id)).filter(InvoiceTemplateModel.is_system_default == True)
        count_result = await db.execute(count_query)
        default_count = count_result.scalar_one_or_none() or 0
        if default_count <= 1:
            # Don't allow unsetting the last system default via a simple update
            # A dedicated endpoint or admin action should handle changing the default.
            # Or, the logic should ensure another is set as default first.
            # For now, we just won't unset it if it's the only one.
            if "is_system_default" in update_data:
                del update_data["is_system_default"] # Remove the change
                print(f"Warning: Attempted to unset the only system default template (ID: {db_obj.id}). Change ignored.")


    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj) # Add db_obj to the session if it's not already there or if it's been modified.
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_invoice_template(db: AsyncSession, *, db_obj: InvoiceTemplateModel) -> InvoiceTemplateModel:
    """
    Delete an invoice template.
    Prevents deletion if it's the system default (or reassigns default - simpler to prevent for now).
    """
    if db_obj.is_system_default:
        # Prevent deletion of the system default template.
        # Admin would need to set another template as default first.
        raise ValueError("Cannot delete the system default invoice template.")
        
    await db.delete(db_obj)
    await db.commit()
    return db_obj