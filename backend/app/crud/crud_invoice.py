from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_ # For complex filtering
from sqlalchemy.orm import selectinload, joinedload # Session for sync delete is not used here
import uuid
from datetime import date
from typing import List, Tuple, Optional # Ensure Optional is imported

from app.models.invoice import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
from app.models.customer import Customer as CustomerModel # For fetching customer name
# Ensure all necessary enums and schemas are imported
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceStatusEnum,
    PricePerTypeEnum, # Crucial for the fix
    InvoiceItemUpdate,
    InvoiceTypeEnum
)

# Helper function to calculate a single line item's total
def _calculate_line_item_total(item_data: InvoiceItemCreate) -> float:
    """Helper to calculate a single line item's total."""
    quantity = 0
    # Access enum by its value if comparing against strings, or compare enum instances directly
    # Assuming item_data.price_per_type is already the correct enum member from Pydantic validation
    if item_data.price_per_type == PricePerTypeEnum.CARTON and item_data.quantity_cartons is not None:
        quantity = item_data.quantity_cartons
    elif item_data.quantity_units is not None: # Default to units if not carton or if carton qty not given
        quantity = item_data.quantity_units
    # If both are None, quantity remains 0, line_total will be 0.
    
    return (item_data.price or 0.0) * quantity

# Helper function to calculate invoice totals
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
    Get a single invoice by its ID, eagerly loading line items, customer, and organization.
    """
    result = await db.execute(
        select(InvoiceModel)
        .options(
            selectinload(InvoiceModel.line_items), 
            joinedload(InvoiceModel.customer),
            joinedload(InvoiceModel.organization) # Added organization loading
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

    # Use status from input, default to DRAFT if not provided (handled by Pydantic default in schema)
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

    for item_data in invoice_in.line_items:
        item_line_total = _calculate_line_item_total(item_data)
        # item_data is already InvoiceItemCreate, so model_dump is fine
        db_item_data_dict = item_data.model_dump()
        db_item = InvoiceItemModel(
            **db_item_data_dict,
            line_total=item_line_total
        )
        db_item.invoice = db_invoice # Establish the relationship
        db.add(db_item)

    await db.commit()
    
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None: 
        raise Exception("Failed to retrieve created invoice after commit.")
    return refreshed_invoice


async def update_invoice_with_items(
    db: AsyncSession, *, db_invoice: InvoiceModel, invoice_in: InvoiceUpdate,
    new_line_items_data: Optional[List[InvoiceItemCreate]] = None
) -> InvoiceModel:
    """
    Update an existing invoice.
    - Updates invoice header fields.
    - If 'new_line_items_data' is provided (or if invoice_in.line_items is set), replaces all existing line items.
    - Handles status and amount_paid consistency.
    """
    # Determine if line items are being replaced (either by dedicated param or from invoice_in schema)
    line_items_to_process = new_line_items_data if new_line_items_data is not None else invoice_in.line_items

    # Ensure existing line items are loaded if we need to access them or clear them
    # This is crucial if we clear the collection db_invoice.line_items.clear()
    if not hasattr(db_invoice, 'line_items') or (line_items_to_process is not None and not db_invoice.line_items):
        await db.refresh(db_invoice, attribute_names=['line_items'])

    update_data = invoice_in.model_dump(exclude_unset=True)
    
    original_status = db_invoice.status
    # original_total_amount = db_invoice.total_amount # Store if needed for complex logic

    # Apply header field updates from invoice_in
    for field, value in update_data.items():
        if field not in ["line_items", "amount_paid", "status"]: # Handle these specially
            setattr(db_invoice, field, value)

    # Handle line item replacement if line_items_to_process is provided
    if line_items_to_process is not None: # Check if a list (even empty) was explicitly passed
        # Clear the existing collection. SQLAlchemy with delete-orphan will mark them for deletion.
        # Ensure line_items were loaded before clearing if db_invoice wasn't just fetched with them.
        await db.refresh(db_invoice, ['line_items']) # Refresh to be sure
        db_invoice.line_items.clear() 
        # await db.flush() # Optional: For immediate DB effect before adding new ones

        for item_data_schema in line_items_to_process: # These are InvoiceItemCreate schemas
            item_line_total = _calculate_line_item_total(item_data_schema)
            # item_data_schema is already a Pydantic model, so model_dump() is fine
            db_item_data_dict = item_data_schema.model_dump() 
            new_db_item = InvoiceItemModel(
                **db_item_data_dict,
                line_total=item_line_total
            )
            new_db_item.invoice = db_invoice # Link to parent
            db_invoice.line_items.append(new_db_item)
    
    # Always recalculate financials
    # current_line_items_for_calc needs to be a list of objects that _calculate_line_item_total expects
    # (i.e., objects with price, price_per_type, quantity_units, quantity_cartons attributes)
    # db_invoice.line_items now contains the ORM models (either old or newly appended ones)
    
    # Re-construct list of Pydantic schemas from ORM models for calculator
    current_line_items_for_calc_schemas: List[InvoiceItemCreate] = []
    if db_invoice.line_items: # If there are any line items (old or new)
        for orm_item in db_invoice.line_items:
            # Convert ORM 'price_per_type' (which is an Enum instance) to its string value
            # for InvoiceItemCreate schema validation.
            price_per_type_value = orm_item.price_per_type.value \
                if isinstance(orm_item.price_per_type, PricePerTypeEnum) \
                else str(orm_item.price_per_type) # Fallback if it's somehow already a string

            item_data_for_schema = {
                "item_description": orm_item.item_description,
                "quantity_cartons": orm_item.quantity_cartons,
                "quantity_units": orm_item.quantity_units,
                "unit_type": orm_item.unit_type, # This is already a string from ORM
                "price": orm_item.price,
                "price_per_type": price_per_type_value, # Use the string value
                "currency": orm_item.currency, # This is already a string from ORM
                "item_specific_comments": orm_item.item_specific_comments,
                "item_id": orm_item.item_id
            }
            # Use model_validate to create an InvoiceItemCreate instance.
            # This also validates the data.
            current_line_items_for_calc_schemas.append(
                InvoiceItemCreate.model_validate(item_data_for_schema)
            )
    
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=current_line_items_for_calc_schemas,
        invoice_currency=db_invoice.currency,
        tax_percentage=db_invoice.tax_percentage,
        discount_percentage=db_invoice.discount_percentage
    )
    db_invoice.subtotal_amount = subtotal
    db_invoice.tax_amount = tax_amt if db_invoice.tax_percentage is not None else (update_data.get('tax_amount', db_invoice.tax_amount))
    db_invoice.discount_amount = discount_amt if db_invoice.discount_percentage is not None else (update_data.get('discount_amount', db_invoice.discount_amount))
    db_invoice.total_amount = total

    # Handle status and amount_paid logic (as refined previously)
    requested_amount_paid = update_data.get("amount_paid")
    requested_status = update_data.get("status")

    if requested_status is not None:
        db_invoice.status = requested_status # Set status from input first
        if db_invoice.status == InvoiceStatusEnum.PAID:
            # If status is set to PAID, amount_paid becomes total_amount unless explicitly provided otherwise
            db_invoice.amount_paid = requested_amount_paid if requested_amount_paid is not None else db_invoice.total_amount
        elif db_invoice.status in [InvoiceStatusEnum.UNPAID, InvoiceStatusEnum.OVERDUE, InvoiceStatusEnum.CANCELLED]:
            if original_status != InvoiceStatusEnum.PARTIALLY_PAID and requested_amount_paid is None:
                 db_invoice.amount_paid = 0.0 # Reset only if not previously partially paid and no new amount given
            elif requested_amount_paid is not None: # If amount_paid is given, respect it
                 db_invoice.amount_paid = requested_amount_paid
        elif db_invoice.status == InvoiceStatusEnum.DRAFT and requested_amount_paid is None: # Default draft to 0 paid
            db_invoice.amount_paid = 0.0
        # For PARTIALLY_PAID status set explicitly, client should also send amount_paid.
        # If they only send status=PARTIALLY_PAID and no amount_paid, amount_paid remains as is or from previous logic.

    # If amount_paid is explicitly provided in the update, set it.
    # Then, if status wasn't also explicitly provided, try to infer status.
    if requested_amount_paid is not None:
        db_invoice.amount_paid = requested_amount_paid
        if requested_status is None: # Only infer status if not explicitly set by client
            if db_invoice.amount_paid >= db_invoice.total_amount and db_invoice.total_amount > 0: # Consider floating point precision
                db_invoice.status = InvoiceStatusEnum.PAID
            elif db_invoice.amount_paid > 0 and db_invoice.amount_paid < db_invoice.total_amount:
                db_invoice.status = InvoiceStatusEnum.PARTIALLY_PAID
            elif db_invoice.amount_paid <= 0:
                # Avoid changing a DRAFT/CANCELLED status to UNPAID just because amount_paid became 0.
                # If it was UNPAID or OVERDUE, it remains so. If it was PAID/PARTIALLY_PAID, it becomes UNPAID.
                if db_invoice.status not in [InvoiceStatusEnum.DRAFT, InvoiceStatusEnum.CANCELLED]:
                    db_invoice.status = InvoiceStatusEnum.UNPAID
    
    db.add(db_invoice) # Ensure invoice itself is marked for update
    await db.commit()
    
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id) # Re-fetch with eager loads
    if refreshed_invoice is None:
        raise Exception(f"Failed to retrieve updated invoice (ID: {db_invoice.id}) after commit.")
    return refreshed_invoice


async def delete_invoice(db: AsyncSession, *, db_invoice: InvoiceModel) -> InvoiceModel:
    """
    Delete an invoice (which also deletes its line items due to cascade if configured).
    """
    await db.delete(db_invoice)
    await db.commit()
    return db_invoice


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
        raise ValueError(f"Invoice with id {invoice_id} not found.")

    line_total = _calculate_line_item_total(item_in)
    # item_in is already InvoiceItemCreate, so model_dump is fine
    db_item_data_dict = item_in.model_dump()
    db_item = InvoiceItemModel(**db_item_data_dict, invoice_id=invoice_id, line_total=line_total)
    # db_item.invoice = parent_invoice # Linking explicitly can also work

    # Add new item to session first to be part of parent_invoice.line_items for recalculation
    db.add(db_item)
    await db.flush([db_item]) # Ensure db_item is in session and linked before recalculating
    await db.refresh(parent_invoice, attribute_names=['line_items']) # Refresh parent to include new item

    all_line_items_data = []
    for li_orm in parent_invoice.line_items:
        item_dict = {
            "item_description": li_orm.item_description,
            "quantity_cartons": li_orm.quantity_cartons,
            "quantity_units": li_orm.quantity_units,
            "unit_type": li_orm.unit_type.value if isinstance(li_orm.unit_type, enum.Enum) else li_orm.unit_type,
            "price": li_orm.price,
            "price_per_type": li_orm.price_per_type.value if isinstance(li_orm.price_per_type, PricePerTypeEnum) else li_orm.price_per_type,
            "currency": li_orm.currency.value if isinstance(li_orm.currency, enum.Enum) else li_orm.currency,
            "item_specific_comments": li_orm.item_specific_comments,
            "item_id": li_orm.item_id
        }
        all_line_items_data.append(InvoiceItemCreate.model_validate(item_dict))
    
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
    await db.refresh(db_item) # Refresh the newly added item
    await db.refresh(parent_invoice) # Refresh parent
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
    # Convert current ORM attributes of db_line_item to dict for InvoiceItemCreate validation
    temp_item_dict_for_calc = {
        "item_description": db_line_item.item_description,
        "quantity_cartons": db_line_item.quantity_cartons,
        "quantity_units": db_line_item.quantity_units,
        "unit_type": db_line_item.unit_type.value if isinstance(db_line_item.unit_type, enum.Enum) else db_line_item.unit_type,
        "price": db_line_item.price,
        "price_per_type": db_line_item.price_per_type.value if isinstance(db_line_item.price_per_type, PricePerTypeEnum) else db_line_item.price_per_type,
        "currency": db_line_item.currency.value if isinstance(db_line_item.currency, enum.Enum) else db_line_item.currency,
        "item_specific_comments": db_line_item.item_specific_comments,
        "item_id": db_line_item.item_id
    }
    line_item_data_for_calc = InvoiceItemCreate.model_validate(temp_item_dict_for_calc)
    db_line_item.line_total = _calculate_line_item_total(line_item_data_for_calc)

    db.add(db_line_item) # Add updated line item to session

    parent_invoice = await get_invoice(db, invoice_id=db_line_item.invoice_id)
    if not parent_invoice: # Should have line_items loaded due to get_invoice
        raise ValueError("Parent invoice not found for line item.")

    all_line_items_data = []
    for li_orm in parent_invoice.line_items: # This will include the updated db_line_item from session
        item_dict = {
             "item_description": li_orm.item_description,
            "quantity_cartons": li_orm.quantity_cartons,
            "quantity_units": li_orm.quantity_units,
            "unit_type": li_orm.unit_type.value if isinstance(li_orm.unit_type, enum.Enum) else li_orm.unit_type,
            "price": li_orm.price,
            "price_per_type": li_orm.price_per_type.value if isinstance(li_orm.price_per_type, PricePerTypeEnum) else li_orm.price_per_type,
            "currency": li_orm.currency.value if isinstance(li_orm.currency, enum.Enum) else li_orm.currency,
            "item_specific_comments": li_orm.item_specific_comments,
            "item_id": li_orm.item_id
        }
        all_line_items_data.append(InvoiceItemCreate.model_validate(item_dict))

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
    parent_invoice_id = db_line_item.invoice_id
    line_item_id_to_exclude = db_line_item.id # Get ID before it's deleted from session

    await db.delete(db_line_item)
    
    parent_invoice = await get_invoice(db, invoice_id=parent_invoice_id) # get_invoice loads line items
    if not parent_invoice:
        await db.commit() 
        return db_line_item 

    all_line_items_data = []
    # After delete and before commit, the item is marked for deletion.
    # parent_invoice.line_items might still contain it until commit if not refreshed.
    # So, explicitly filter it out.
    for li_orm in parent_invoice.line_items:
        if li_orm.id != line_item_id_to_exclude: # Exclude the item being deleted
            item_dict = {
                "item_description": li_orm.item_description,
                "quantity_cartons": li_orm.quantity_cartons,
                "quantity_units": li_orm.quantity_units,
                "unit_type": li_orm.unit_type.value if isinstance(li_orm.unit_type, enum.Enum) else li_orm.unit_type,
                "price": li_orm.price,
                "price_per_type": li_orm.price_per_type.value if isinstance(li_orm.price_per_type, PricePerTypeEnum) else li_orm.price_per_type,
                "currency": li_orm.currency.value if isinstance(li_orm.currency, enum.Enum) else li_orm.currency,
                "item_specific_comments": li_orm.item_specific_comments,
                "item_id": li_orm.item_id
            }
            all_line_items_data.append(InvoiceItemCreate.model_validate(item_dict))

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
    return db_line_item


async def transform_pro_forma_to_commercial(
    db: AsyncSession, *, pro_forma_invoice: InvoiceModel, new_invoice_number: Optional[str] = None
) -> InvoiceModel:
    """
    Creates a new Commercial invoice based on an existing Pro Forma invoice.
    Copies line items and relevant header data.
    """
    if pro_forma_invoice.invoice_type != InvoiceTypeEnum.PRO_FORMA:
        raise ValueError("Only Pro Forma invoices can be transformed.")
    
    # Ensure line items are loaded for copying
    if not pro_forma_invoice.line_items: # Pro forma might have been fetched without line_items
        await db.refresh(pro_forma_invoice, attribute_names=['line_items'])

    new_line_items_create_data: List[InvoiceItemCreate] = []
    if pro_forma_invoice.line_items:
        for li in pro_forma_invoice.line_items:
            # Assuming PricePerTypeEnum needs its .value if the ORM field is an enum object
            price_per_type_val = li.price_per_type.value if isinstance(li.price_per_type, PricePerTypeEnum) else li.price_per_type
            unit_type_val = li.unit_type.value if isinstance(li.unit_type, enum.Enum) else li.unit_type
            currency_val = li.currency.value if isinstance(li.currency, enum.Enum) else li.currency
            
            new_line_items_create_data.append(
                InvoiceItemCreate(
                    item_description=li.item_description,
                    quantity_cartons=li.quantity_cartons,
                    quantity_units=li.quantity_units,
                    unit_type=unit_type_val,
                    price=li.price,
                    price_per_type=price_per_type_val,
                    currency=currency_val,
                    item_specific_comments=li.item_specific_comments,
                    item_id=li.item_id # FK to product/service Item
                )
            )
    
    final_new_invoice_number = new_invoice_number or f"{pro_forma_invoice.invoice_number}-C" # Improve numbering

    commercial_invoice_create_data = InvoiceCreate(
        invoice_number=final_new_invoice_number,
        invoice_date=date.today(), 
        due_date=pro_forma_invoice.due_date, 
        invoice_type=InvoiceTypeEnum.COMMERCIAL,
        status=InvoiceStatusEnum.DRAFT, 
        currency=pro_forma_invoice.currency,
        organization_id=pro_forma_invoice.organization_id,
        customer_id=pro_forma_invoice.customer_id,
        tax_percentage=pro_forma_invoice.tax_percentage,
        discount_percentage=pro_forma_invoice.discount_percentage,
        comments_notes=pro_forma_invoice.comments_notes,
        line_items=new_line_items_create_data,
        # Exclude user_id; it's set by owner_id in create_invoice_with_items
        # Exclude amount_paid; new commercial invoice has 0 paid initially
        # Exclude pdf_url
    )

    new_commercial_invoice = await create_invoice_with_items(
        db=db,
        invoice_in=commercial_invoice_create_data,
        owner_id=pro_forma_invoice.user_id
    )
    
    return new_commercial_invoice