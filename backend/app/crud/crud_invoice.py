from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_ # For complex filtering
from sqlalchemy.orm import selectinload, joinedload, Session # Session for sync delete
import uuid
from datetime import date
from typing import List, Tuple, Optional # Ensure Optional is imported

from app.models.invoice import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
from app.models.customer import Customer as CustomerModel # For fetching customer name
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, InvoiceStatusEnum, PricePerTypeEnum, InvoiceItemUpdate

# Helper function to calculate invoice totals
def _calculate_line_item_total(item_data: InvoiceItemCreate) -> float:
    """Helper to calculate a single line item's total."""
    quantity = 0
    if item_data.price_per_type == PricePerTypeEnum.CARTON and item_data.quantity_cartons is not None:
        quantity = item_data.quantity_cartons
    elif item_data.quantity_units is not None: # Default to units if not carton or if carton qty not given
        quantity = item_data.quantity_units
    # If both are None, quantity remains 0, line_total will be 0. Price must be positive if set.
    
    return (item_data.price or 0.0) * quantity

def calculate_invoice_financials(
    line_items_data: List[InvoiceItemCreate], 
    invoice_currency: str, 
    tax_percentage: Optional[float] = None,
    discount_percentage: Optional[float] = None
) -> Tuple[float, float, float, float]:
    """
    Calculates subtotal, tax, discount, and total for an invoice.
    V1: Assumes all line item currencies are the same as invoice_currency.
    """
    subtotal = 0.0
    for item_data in line_items_data:
        line_total = _calculate_line_item_total(item_data)
        # V1 Simplification: Assume item_data.currency matches invoice_currency.
        subtotal += line_total

    calculated_tax_amount = 0.0
    if tax_percentage is not None and tax_percentage > 0:
        calculated_tax_amount = round(subtotal * (tax_percentage / 100.0), 2)

    calculated_discount_amount = 0.0
    if discount_percentage is not None and discount_percentage > 0:
        calculated_discount_amount = round(subtotal * (discount_percentage / 100.0), 2)
    
    calculated_discount_amount = min(calculated_discount_amount, subtotal) # Cap discount

    total = round(subtotal + calculated_tax_amount - calculated_discount_amount, 2)

    return round(subtotal, 2), calculated_tax_amount, calculated_discount_amount, total


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Optional[InvoiceModel]:
    """
    Get a single invoice by its ID, eagerly loading line items and customer.
    """
    result = await db.execute(
        select(InvoiceModel)
        .options(
            selectinload(InvoiceModel.line_items), 
            joinedload(InvoiceModel.customer),
            joinedload(InvoiceModel.organization)     
        )
        .filter(InvoiceModel.id == invoice_id)
    )
    return result.scalars().first()

async def get_invoices_by_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
    status: Optional[InvoiceStatusEnum] = None,
    customer_id: Optional[uuid.UUID] = None,
    invoice_number_search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> List[InvoiceModel]:
    """
    Get a list of invoices for a specific user, with various filters and pagination.
    """
    query = (
        select(InvoiceModel)
        .options(joinedload(InvoiceModel.customer)) 
        .filter(InvoiceModel.user_id == user_id)
        .order_by(InvoiceModel.invoice_date.desc(), InvoiceModel.invoice_number.desc())
    )

    if organization_id:
        query = query.filter(InvoiceModel.organization_id == organization_id)
    if status:
        query = query.filter(InvoiceModel.status == status)
    if customer_id:
        query = query.filter(InvoiceModel.customer_id == customer_id)
    if invoice_number_search:
        query = query.filter(InvoiceModel.invoice_number.ilike(f"%{invoice_number_search}%"))
    if date_from:
        query = query.filter(InvoiceModel.invoice_date >= date_from)
    if date_to:
        query = query.filter(InvoiceModel.invoice_date <= date_to)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def create_invoice_with_items(
    db: AsyncSession, *, invoice_in: InvoiceCreate, owner_id: uuid.UUID
) -> InvoiceModel:
    """
    Create a new invoice and its line items. Calculates financial totals.
    """
    invoice_data_dict = invoice_in.model_dump(
        exclude={'line_items', 'subtotal_amount', 'tax_amount', 'discount_amount', 'total_amount', 'pdf_url', 'status'}
    )
    
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=invoice_in.line_items,
        invoice_currency=invoice_in.currency,
        tax_percentage=invoice_in.tax_percentage,
        discount_percentage=invoice_in.discount_percentage
    )

    final_status = invoice_in.status

    db_invoice = InvoiceModel(
        **invoice_data_dict,
        user_id=owner_id,
        subtotal_amount=subtotal,
        tax_amount=tax_amt if invoice_in.tax_percentage is not None else (invoice_in.tax_amount or 0.0),
        discount_amount=discount_amt if invoice_in.discount_percentage is not None else (invoice_in.discount_amount or 0.0),
        total_amount=total,
        status=final_status
    )
    db.add(db_invoice)
    # Flush to get db_invoice.id if not already available for relationship linking below,
    # or rely on SQLAlchemy to handle it during commit if db_item.invoice is set.
    # await db.flush([db_invoice]) # Optional: flush to get ID if needed immediately

    for item_data in invoice_in.line_items:
        item_line_total = _calculate_line_item_total(item_data)
        db_item_data = item_data.model_dump()
        db_item = InvoiceItemModel(
            **db_item_data,
            line_total=item_line_total
            # invoice_id=db_invoice.id # Will be set if db_invoice is flushed or via relationship
        )
        db_item.invoice = db_invoice # Establish the relationship
        db.add(db_item)

    await db.commit()
    # await db.refresh(db_invoice, attribute_names=['line_items']) # Refresh with line_items
    
    # Re-fetch the invoice to ensure all relationships (like line_items) are loaded
    # as defined in the get_invoice function (which uses selectinload).
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None: # Should not happen if commit was successful
        raise Exception("Failed to retrieve created invoice after commit.")
    return refreshed_invoice


async def update_invoice_with_items(
    db: AsyncSession, *, db_invoice: InvoiceModel, invoice_in: InvoiceUpdate,
    new_line_items_data: Optional[List[InvoiceItemCreate]] = None # For full replacement
) -> InvoiceModel:
    """
    Update an existing invoice.
    - Updates invoice header fields.
    - If 'new_line_items_data' is provided, replaces all existing line items.
    """
    # Ensure existing line items are loaded for deletion and recalculation
    # This relies on db_invoice (passed in) having its line_items loaded,
    # typically ensured by how get_invoice (which uses selectinload) fetches it.
    if not hasattr(db_invoice, 'line_items') or not db_invoice.line_items:
        # If not loaded, explicitly load them
        await db.refresh(db_invoice, attribute_names=['line_items'])

    update_data = invoice_in.model_dump(exclude_unset=True) # Get all update fields
    
    # Update header fields
    for field, value in update_data.items():
        if field != "line_items": # line_items handled separately if new_line_items_data is given
            setattr(db_invoice, field, value)

    # Handle line item replacement if new_line_items_data is provided
    if new_line_items_data is not None:
        # 1. Delete old line items. Iterate over a copy if modifying the collection.
        # Using db.delete and relying on cascade might be cleaner for bulk operations.
        # Here, explicit delete and clearing the collection.
        # This makes sure that even if cascade isn't perfectly set up, they are gone.
        
        # Efficiently delete existing items associated with this invoice
        # This direct delete avoids iterating and deleting one by one if cascade is not used
        # or if we want to be very explicit.
        # However, SQLAlchemy's ORM cascade="all, delete-orphan" on the relationship
        # should handle this if we just clear the collection and add new ones.
        
        # Let's rely on "delete-orphan" cascade.
        # Fetch existing line items (if not already loaded and up-to-date)
        # This ensures we are working with the current state.
        await db.refresh(db_invoice, ['line_items'])
        
        # Clear the existing collection. SQLAlchemy with delete-orphan will mark them for deletion.
        db_invoice.line_items.clear()
        # For immediate deletion in DB before adding new ones, could flush here:
        # await db.flush()

        # 2. Add new line items
        for item_data in new_line_items_data:
            item_line_total = _calculate_line_item_total(item_data)
            db_item_data = item_data.model_dump()
            new_db_item = InvoiceItemModel(
                **db_item_data,
                line_total=item_line_total
                # invoice_id=db_invoice.id # Handled by relationship
            )
            new_db_item.invoice = db_invoice # Link to parent
            db_invoice.line_items.append(new_db_item) # Add to collection
            # db.add(new_db_item) # Adding through collection is often enough if cascade is set

    # Always recalculate financials after any potential header or line item change
    # For calculate_invoice_financials, we need data in InvoiceItemCreate format.
    # Convert current ORM line items (which might be new or existing) to schemas.
    current_line_items_for_calc: List[InvoiceItemCreate] = []
    for orm_item in db_invoice.line_items: # These are the items that will be in the DB after commit
        # If orm_item is newly created and not yet committed, it might not have all fields.
        # We need to ensure the data passed to InvoiceItemCreate.model_validate is complete.
        # A simple way is to use the data intended for the DB.
        # This requires careful handling of item_id if it's meant to be from an existing product.
        # For now, assume all necessary fields for InvoiceItemCreate are present on orm_item.
        
        # If orm_item.price_per_type is an enum, convert to str for model_validate if needed
        price_per_type_str = orm_item.price_per_type.value if isinstance(orm_item.price_per_type, PricePerTypeEnum) else orm_item.price_per_type

        current_line_items_for_calc.append(
            InvoiceItemCreate(
                item_description=orm_item.item_description,
                quantity_cartons=orm_item.quantity_cartons,
                quantity_units=orm_item.quantity_units,
                unit_type=orm_item.unit_type,
                price=orm_item.price,
                price_per_type=price_per_type_str, # Use string value of enum
                currency=orm_item.currency,
                item_specific_comments=orm_item.item_specific_comments,
                item_id=orm_item.item_id
            )
        )

    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=current_line_items_for_calc,
        invoice_currency=db_invoice.currency,
        tax_percentage=db_invoice.tax_percentage,
        discount_percentage=db_invoice.discount_percentage
    )
    db_invoice.subtotal_amount = subtotal
    # Prioritize calculated tax/discount if percentages are set
    db_invoice.tax_amount = tax_amt if db_invoice.tax_percentage is not None else (update_data.get('tax_amount', db_invoice.tax_amount))
    db_invoice.discount_amount = discount_amt if db_invoice.discount_percentage is not None else (update_data.get('discount_amount', db_invoice.discount_amount))
    db_invoice.total_amount = total
    
    db.add(db_invoice) # Ensure invoice itself is added to session for updates
    await db.commit()
    # await db.refresh(db_invoice, attribute_names=['line_items'])
    
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None:
        raise Exception("Failed to retrieve updated invoice after commit.")
    return refreshed_invoice


async def delete_invoice(db: AsyncSession, *, db_invoice: InvoiceModel) -> InvoiceModel:
    """
    Delete an invoice (which also deletes its line items due to cascade if configured).
    """
    # Ensure line items are loaded if not already, for logging or pre-delete actions if any.
    # However, cascade delete should handle this from DB side.
    await db.delete(db_invoice)
    await db.commit()
    return db_invoice # Return the object as it was (now detached)

# --- CRUD for Individual InvoiceItems (Example, if needed for separate endpoints) ---
async def get_invoice_line_item(db: AsyncSession, invoice_item_id: uuid.UUID) -> Optional[InvoiceItemModel]:
    result = await db.execute(select(InvoiceItemModel).filter(InvoiceItemModel.id == invoice_item_id))
    return result.scalars().first()

async def add_line_item_to_invoice(
    db: AsyncSession, *, item_in: InvoiceItemCreate, invoice_id: uuid.UUID
) -> InvoiceItemModel:
    """
    Adds a single line item to an existing invoice and recalculates invoice totals.
    """
    parent_invoice = await get_invoice(db, invoice_id=invoice_id)
    if not parent_invoice:
        raise ValueError(f"Invoice with id {invoice_id} not found.") # Or appropriate exception

    line_total = _calculate_line_item_total(item_in)
    db_item = InvoiceItemModel(**item_in.model_dump(), invoice_id=invoice_id, line_total=line_total)
    db_item.invoice = parent_invoice # Link
    
    db.add(db_item)
    # No commit yet, totals need recalculation

    # Recalculate totals for the parent invoice
    # First, get all current line items including the new one (which is in session but not DB yet)
    all_line_items_data = [
        InvoiceItemCreate.model_validate(li) for li in parent_invoice.line_items
    ]
    all_line_items_data.append(item_in) # Add the data of the new item

    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data,
        invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage,
        discount_percentage=parent_invoice.discount_percentage
    )
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    
    db.add(parent_invoice) # Add updated parent invoice to session
    await db.commit()
    await db.refresh(db_item)
    await db.refresh(parent_invoice) # Refresh parent to get updated totals and new item in collection
    return db_item

async def update_invoice_line_item(
    db: AsyncSession, *, db_line_item: InvoiceItemModel, item_in: InvoiceItemUpdate
) -> InvoiceItemModel:
    """
    Updates a single line item and recalculates parent invoice totals.
    """
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_line_item, field, value)
    
    # Recalculate this line item's total
    line_item_data_for_calc = InvoiceItemCreate.model_validate(db_line_item) # Convert ORM to schema
    db_line_item.line_total = _calculate_line_item_total(line_item_data_for_calc)

    db.add(db_line_item)
    # No commit yet, parent invoice totals need recalculation

    parent_invoice = await get_invoice(db, invoice_id=db_line_item.invoice_id)
    if not parent_invoice:
        raise ValueError("Parent invoice not found for line item.")

    # Recalculate totals for the parent invoice
    all_line_items_data = [
        InvoiceItemCreate.model_validate(li) for li in parent_invoice.line_items
    ]
    # Note: parent_invoice.line_items here will include the updated db_line_item if session is managed correctly.

    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data,
        invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage,
        discount_percentage=parent_invoice.discount_percentage
    )
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total

    db.add(parent_invoice)
    await db.commit()
    await db.refresh(db_line_item)
    await db.refresh(parent_invoice)
    return db_line_item

async def delete_invoice_line_item(db: AsyncSession, *, db_line_item: InvoiceItemModel) -> InvoiceItemModel:
    """
    Deletes a single line item and recalculates parent invoice totals.
    """
    parent_invoice_id = db_line_item.invoice_id # Get ID before deleting
    await db.delete(db_line_item)
    # No commit yet, parent invoice totals need recalculation

    parent_invoice = await get_invoice(db, invoice_id=parent_invoice_id)
    if not parent_invoice:
        # This case should be rare if FKs are in place, but good to handle
        await db.commit() # Commit the line item deletion anyway
        return db_line_item # Return the detached item

    # Recalculate totals for the parent invoice
    # parent_invoice.line_items will now exclude the deleted item after refresh or re-query
    # Await db.refresh(parent_invoice, ['line_items']) # Or ensure get_invoice re-fetches cleanly

    all_line_items_data = [
        InvoiceItemCreate.model_validate(li) for li in parent_invoice.line_items if li.id != db_line_item.id
    ] # Exclude the one being deleted

    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data,
        invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage,
        discount_percentage=parent_invoice.discount_percentage
    )
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    
    db.add(parent_invoice)
    await db.commit()
    # await db.refresh(parent_invoice) # No need to refresh parent if just totals changed
    return db_line_item # Return the deleted item (now detached)