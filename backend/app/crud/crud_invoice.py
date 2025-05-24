from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_ 
from sqlalchemy.orm import selectinload, joinedload
import uuid
from datetime import date
from typing import List, Tuple, Optional 

from app.models.invoice import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
from app.models.customer import Customer as CustomerModel
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceStatusEnum,
    PricePerTypeEnum, 
    InvoiceItemUpdate,
    InvoiceTypeEnum
)

# Helper function to calculate a single line item's total
def _calculate_line_item_total(item_data: InvoiceItemCreate) -> float:
    """Helper to calculate a single line item's total."""
    price = item_data.price or 0.0 
    quantity = 0
    if item_data.price_per_type == PricePerTypeEnum.CARTON and item_data.quantity_cartons is not None:
        quantity = item_data.quantity_cartons
    elif item_data.quantity_units is not None: 
        quantity = item_data.quantity_units
    
    final_quantity = float(quantity) if quantity is not None else 0.0
    final_price = float(price) 
    calculated_total = round(final_price * final_quantity, 2)
    print(f"    DEBUG (_calculate_line_item_total): Desc='{item_data.item_description}', Price={final_price}, Qty={final_quantity}, LineTotal={calculated_total}")
    return calculated_total

# Helper function to calculate invoice totals
def calculate_invoice_financials(
    line_items_data: List[InvoiceItemCreate], 
    invoice_currency: str, 
    tax_percentage: Optional[float] = None,
    discount_percentage: Optional[float] = None
) -> Tuple[float, float, float, float]:
    """
    Calculates subtotal, tax, discount, and total for an invoice.
    """
    print(f"  DEBUG (calculate_invoice_financials): Received {len(line_items_data)} line items for calculation.")
    subtotal = 0.0
    for idx, item_data in enumerate(line_items_data):
        print(f"  DEBUG (calculate_invoice_financials): Processing line item #{idx + 1}: Description='{item_data.item_description}', Price={item_data.price}, QtyUnits={item_data.quantity_units}, QtyCartons={item_data.quantity_cartons}, PricePerType={item_data.price_per_type}")
        line_total = _calculate_line_item_total(item_data)
        subtotal += line_total
    
    subtotal = round(subtotal, 2) 
    print(f"  DEBUG (calculate_invoice_financials): Calculated Raw Subtotal (after rounding) = {subtotal}")

    calculated_tax_amount = 0.0
    if tax_percentage is not None and tax_percentage > 0:
        calculated_tax_amount = round(subtotal * (tax_percentage / 100.0), 2)

    calculated_discount_amount = 0.0
    if discount_percentage is not None and discount_percentage > 0:
        calculated_discount_amount = round(subtotal * (discount_percentage / 100.0), 2)
    
    calculated_discount_amount = min(calculated_discount_amount, subtotal) 

    total = round(subtotal + calculated_tax_amount - calculated_discount_amount, 2)
    print(f"  DEBUG (calculate_invoice_financials): Returning: Sub={subtotal}, Tax={calculated_tax_amount}, Disc={calculated_discount_amount}, Total={total}")
    return subtotal, calculated_tax_amount, calculated_discount_amount, total


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Optional[InvoiceModel]:
    """
    Get a single invoice by its ID, eagerly loading line items (and their related item for image_url), 
    customer, and organization.
    """
    result = await db.execute(
        select(InvoiceModel)
        .options(
            joinedload(InvoiceModel.customer),
            joinedload(InvoiceModel.organization),
            selectinload(InvoiceModel.line_items).selectinload(InvoiceItemModel.item) # <--- CRUCIAL LINE FOR ITEM IMAGE
        )
        .filter(InvoiceModel.id == invoice_id)
    )
    invoice = result.scalars().first()

    return invoice

async def get_invoices_by_user(
    db: AsyncSession, *, user_id: uuid.UUID, organization_id: Optional[uuid.UUID] = None,
    status: Optional[InvoiceStatusEnum] = None, customer_id: Optional[uuid.UUID] = None,
    invoice_number_search: Optional[str] = None, date_from: Optional[date] = None,
    date_to: Optional[date] = None, skip: int = 0, limit: int = 100
) -> List[InvoiceModel]:
    query = (
        select(InvoiceModel)
        .options(joinedload(InvoiceModel.customer)) 
        .filter(InvoiceModel.user_id == user_id)
        .order_by(InvoiceModel.invoice_date.desc(), InvoiceModel.invoice_number.desc())
    )
    if organization_id: query = query.filter(InvoiceModel.organization_id == organization_id)
    if status: query = query.filter(InvoiceModel.status == status)
    if customer_id: query = query.filter(InvoiceModel.customer_id == customer_id)
    if invoice_number_search: query = query.filter(InvoiceModel.invoice_number.ilike(f"%{invoice_number_search}%"))
    if date_from: query = query.filter(InvoiceModel.invoice_date >= date_from)
    if date_to: query = query.filter(InvoiceModel.invoice_date <= date_to)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def create_invoice_with_items(
    db: AsyncSession, *, invoice_in: InvoiceCreate, owner_id: uuid.UUID
) -> InvoiceModel:
    print(f"\n--- DEBUG: Entering create_invoice_with_items ---")
    print(f"DEBUG: Raw invoice_in.line_items (from API/frontend payload): {invoice_in.line_items}")
    invoice_data_dict = invoice_in.model_dump(
        exclude={'line_items', 'subtotal_amount', 'tax_amount', 'discount_amount', 'total_amount', 'pdf_url', 'status'}
    )
    print(f"DEBUG: Line items being passed to calculate_invoice_financials: {invoice_in.line_items}")
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=invoice_in.line_items, 
        invoice_currency=invoice_in.currency,
        tax_percentage=invoice_in.tax_percentage,
        discount_percentage=invoice_in.discount_percentage
    )
    print(f"DEBUG: Financials returned by calculator in create_invoice_with_items: Sub={subtotal}, Tax={tax_amt}, Disc={discount_amt}, Total={total}")
    final_status = invoice_in.status 
    db_invoice = InvoiceModel(
        **invoice_data_dict, user_id=owner_id, subtotal_amount=subtotal,
        tax_amount=tax_amt if invoice_in.tax_percentage is not None else (invoice_in.tax_amount or 0.0),
        discount_amount=discount_amt if invoice_in.discount_percentage is not None else (invoice_in.discount_amount or 0.0),
        total_amount=total, status=final_status
    )
    print(f"DEBUG: InvoiceModel instance before adding to session: total_amount={db_invoice.total_amount}, subtotal_amount={db_invoice.subtotal_amount}")
    db.add(db_invoice)
    for item_data_schema in invoice_in.line_items:
        item_line_db_total = _calculate_line_item_total(item_data_schema) 
        print(f"DEBUG: Line item from invoice_in: '{item_data_schema.item_description}', its individual calculated line_total for DB: {item_line_db_total}")
        db_item_data = item_data_schema.model_dump()
        db_item = InvoiceItemModel(**db_item_data, line_total=item_line_db_total)
        db_item.invoice = db_invoice 
        db.add(db_item)
    await db.commit()
    print(f"DEBUG: After db.commit(), Invoice ID: {db_invoice.id}, Total from ORM object: {db_invoice.total_amount}")
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None: raise Exception("Failed to retrieve created invoice after commit.")
    print(f"DEBUG: Refreshed invoice (after get_invoice call) total: {refreshed_invoice.total_amount}")
    print(f"--- DEBUG: Exiting create_invoice_with_items ---\n")
    return refreshed_invoice

# --- Updated update_invoice_with_items function ---
async def update_invoice_with_items(
    db: AsyncSession, *, db_invoice: InvoiceModel, invoice_in: InvoiceUpdate
) -> InvoiceModel:
    print(f"\n--- DEBUG: Entering update_invoice_with_items for Invoice ID: {db_invoice.id} ---")
    print(f"DEBUG: Raw invoice_in from API: {invoice_in}") # invoice_in is InvoiceUpdate

    # Ensure existing line items are loaded if we need to clear them or refer to them,
    # especially if line_items are part of the update payload.
    # model_fields_set (Pydantic V2) tells us if 'line_items' was explicitly in the payload.
    if 'line_items' in invoice_in.model_fields_set:
        print(f"DEBUG (update): 'line_items' field was set in payload. Refreshing existing line_items on db_invoice.")
        await db.refresh(db_invoice, attribute_names=['line_items'])

    # We only want to update header fields that were actually sent (exclude_unset=True)
    # And exclude 'line_items' because they are handled specially.
    update_data_header = invoice_in.model_dump(exclude_unset=True, exclude={'line_items'})
    
    original_status = db_invoice.status

    # Apply header field updates
    for field, value in update_data_header.items():
        # Skip amount_paid and status here, they are handled after total recalculation
        if field not in ["amount_paid", "status"]:
            setattr(db_invoice, field, value)

    line_items_for_calculation: List[InvoiceItemCreate]

    # Handle line item replacement if 'line_items' is explicitly in the payload (and not None)
    if 'line_items' in invoice_in.model_fields_set and invoice_in.line_items is not None:
        print(f"DEBUG (update): Replacing line items. Received {len(invoice_in.line_items)} new items from payload.")
        
        # Clear the existing collection. SQLAlchemy with delete-orphan will mark them for deletion.
        db_invoice.line_items.clear() 
        # await db.flush() # Optional: if immediate DB deletion is critical before adding new.

        new_orm_line_items = []
        for item_data_schema in invoice_in.line_items: # These are InvoiceItemCreate from payload
            item_line_total = _calculate_line_item_total(item_data_schema) # Instrumented
            # print(f"DEBUG (update): New line item from input: '{item_data_schema.item_description}', its individual calculated line_total for DB: {item_line_total}")
            db_item_data_dict = item_data_schema.model_dump()
            new_db_item = InvoiceItemModel(
                **db_item_data_dict,
                line_total=item_line_total
            )
            # new_db_item.invoice = db_invoice # Relationship set by appending to collection
            new_orm_line_items.append(new_db_item)
        
        db_invoice.line_items = new_orm_line_items # Assign the new list of ORM items to the relationship
        line_items_for_calculation = list(invoice_in.line_items) # Use the input Pydantic schemas for calculation
        print(f"DEBUG (update): After setting new items, db_invoice.line_items (ORM models) count for DB: {len(db_invoice.line_items)}")
    else:
        # Line items were NOT in the payload (or were explicitly None), so use existing ones from db_invoice for calculation.
        # Ensure they are loaded if not already.
        if not db_invoice.line_items or not all(isinstance(li, InvoiceItemModel) for li in db_invoice.line_items): # Check if loaded
            print(f"DEBUG (update): 'line_items' not in payload or None. Refreshing existing line_items on db_invoice.")
            await db.refresh(db_invoice, attribute_names=['line_items'])
        
        print(f"DEBUG (update): Using existing {len(db_invoice.line_items)} ORM line items for recalculation.")
        # Convert existing ORM items to Pydantic InvoiceItemCreate schemas for the calculator
        line_items_for_calculation = []
        for orm_item in db_invoice.line_items:
            line_items_for_calculation.append(
                InvoiceItemCreate( # This assumes direct attribute mapping works
                    item_description=orm_item.item_description,
                    quantity_cartons=orm_item.quantity_cartons,
                    quantity_units=orm_item.quantity_units,
                    unit_type=orm_item.unit_type,
                    price=orm_item.price,
                    price_per_type=orm_item.price_per_type, # Pass ORM enum instance
                    currency=orm_item.currency,
                    item_specific_comments=orm_item.item_specific_comments,
                    item_id=orm_item.item_id
                )
            )

    print(f"DEBUG (update): Line items being passed to calculate_invoice_financials ({len(line_items_for_calculation)} items): {line_items_for_calculation}")
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=line_items_for_calculation, 
        invoice_currency=db_invoice.currency, # Use current (possibly updated) currency
        tax_percentage=db_invoice.tax_percentage, # Use current (possibly updated) tax_percentage
        discount_percentage=db_invoice.discount_percentage # Use current (possibly updated) discount_percentage
    )
    print(f"DEBUG (update): Financials returned by calculator: Sub={subtotal}, Tax={tax_amt}, Disc={discount_amt}, Total={total}")
    
    db_invoice.subtotal_amount = subtotal
    # Use updated value if percentage is source, otherwise from payload (if sent), else existing
    db_invoice.tax_amount = tax_amt if db_invoice.tax_percentage is not None else (update_data_header.get('tax_amount', db_invoice.tax_amount))
    db_invoice.discount_amount = discount_amt if db_invoice.discount_percentage is not None else (update_data_header.get('discount_amount', db_invoice.discount_amount))
    db_invoice.total_amount = total # Always use recalculated total

    # Handle status and amount_paid logic (as refined previously)
    # Use update_data_header to see if 'amount_paid' or 'status' were in the original payload
    requested_amount_paid = update_data_header.get("amount_paid") 
    requested_status = update_data_header.get("status")

    if requested_status is not None: # If status was in the update payload
        db_invoice.status = requested_status
        if db_invoice.status == InvoiceStatusEnum.PAID:
            db_invoice.amount_paid = requested_amount_paid if requested_amount_paid is not None else db_invoice.total_amount
        elif db_invoice.status in [InvoiceStatusEnum.UNPAID, InvoiceStatusEnum.OVERDUE, InvoiceStatusEnum.CANCELLED]:
            if original_status != InvoiceStatusEnum.PARTIALLY_PAID and requested_amount_paid is None:
                 db_invoice.amount_paid = 0.0
            elif requested_amount_paid is not None:
                 db_invoice.amount_paid = requested_amount_paid
        elif db_invoice.status == InvoiceStatusEnum.DRAFT and requested_amount_paid is None:
            db_invoice.amount_paid = 0.0
    
    if requested_amount_paid is not None: # If amount_paid was in the update payload
        db_invoice.amount_paid = requested_amount_paid
        if requested_status is None: # Only infer status if status wasn't also in the payload
            if db_invoice.amount_paid >= db_invoice.total_amount and db_invoice.total_amount > 0:
                db_invoice.status = InvoiceStatusEnum.PAID
            elif db_invoice.amount_paid > 0 and db_invoice.amount_paid < db_invoice.total_amount:
                db_invoice.status = InvoiceStatusEnum.PARTIALLY_PAID
            elif db_invoice.amount_paid <= 0:
                if db_invoice.status not in [InvoiceStatusEnum.DRAFT, InvoiceStatusEnum.CANCELLED]:
                    db_invoice.status = InvoiceStatusEnum.UNPAID
    
    print(f"DEBUG (update): InvoiceModel instance before commit: total_amount={db_invoice.total_amount}, subtotal_amount={db_invoice.subtotal_amount}, status={db_invoice.status}, amount_paid={db_invoice.amount_paid}")
    db.add(db_invoice) # Ensure the invoice object (now modified) is in the session to be updated
    await db.commit()
    print(f"DEBUG (update): After db.commit(), Invoice ID: {db_invoice.id}, Total from ORM object: {db_invoice.total_amount}")
    
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None:
        raise Exception(f"Failed to retrieve updated invoice (ID: {db_invoice.id}) after commit.")
    print(f"DEBUG (update): Refreshed invoice (after get_invoice call) total: {refreshed_invoice.total_amount}")
    print(f"--- DEBUG: Exiting update_invoice_with_items for Invoice ID: {db_invoice.id} ---\n")
    return refreshed_invoice


async def delete_invoice(db: AsyncSession, *, db_invoice: InvoiceModel) -> InvoiceModel:
    await db.delete(db_invoice)
    await db.commit()
    return db_invoice

async def get_invoice_line_item(db: AsyncSession, invoice_item_id: uuid.UUID) -> Optional[InvoiceItemModel]:
    result = await db.execute(select(InvoiceItemModel).filter(InvoiceItemModel.id == invoice_item_id))
    return result.scalars().first()

async def add_line_item_to_invoice(
    db: AsyncSession, *, item_in: InvoiceItemCreate, invoice_id: uuid.UUID
) -> InvoiceItemModel:
    print(f"\n--- DEBUG: Entering add_line_item_to_invoice for Invoice ID: {invoice_id} ---")
    print(f"DEBUG (add_li): item_in: {item_in}")
    parent_invoice = await get_invoice(db, invoice_id=invoice_id)
    if not parent_invoice: raise ValueError(f"Invoice with id {invoice_id} not found.")
    line_total = _calculate_line_item_total(item_in)
    db_item_data_dict = item_in.model_dump()
    db_item = InvoiceItemModel(**db_item_data_dict, invoice_id=invoice_id, line_total=line_total)
    db.add(db_item)
    await db.flush([db_item]) 
    await db.refresh(parent_invoice, attribute_names=['line_items'])
    all_line_items_data: List[InvoiceItemCreate] = []
    if parent_invoice.line_items:
        for li_orm in parent_invoice.line_items:
            all_line_items_data.append(
                InvoiceItemCreate(
                    item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                    quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, price=li_orm.price,
                    price_per_type=li_orm.price_per_type, currency=li_orm.currency,
                    item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id
                )
            )
    print(f"DEBUG (add_li): Line items for recalculation: {all_line_items_data}")
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
    )
    print(f"DEBUG (add_li): Recalculated parent totals: Sub={subtotal}, Tax={tax_amt}, Disc={discount_amt}, Total={total}")
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    db.add(parent_invoice)
    await db.commit()
    await db.refresh(db_item); await db.refresh(parent_invoice)
    print(f"--- DEBUG: Exiting add_line_item_to_invoice. New item ID: {db_item.id}, Parent Total: {parent_invoice.total_amount} ---\n")
    return db_item

async def update_invoice_line_item(
    db: AsyncSession, *, db_line_item: InvoiceItemModel, item_in: InvoiceItemUpdate
) -> InvoiceItemModel:
    print(f"\n--- DEBUG: Entering update_invoice_line_item for Line Item ID: {db_line_item.id} ---")
    print(f"DEBUG (update_li): item_in: {item_in}")
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items(): setattr(db_line_item, field, value)
    temp_item_for_calc = InvoiceItemCreate(
        item_description=db_line_item.item_description, quantity_cartons=db_line_item.quantity_cartons,
        quantity_units=db_line_item.quantity_units, unit_type=db_line_item.unit_type, price=db_line_item.price,
        price_per_type=db_line_item.price_per_type, currency=db_line_item.currency,
        item_specific_comments=db_line_item.item_specific_comments, item_id=db_line_item.item_id
    )
    db_line_item.line_total = _calculate_line_item_total(temp_item_for_calc)
    print(f"DEBUG (update_li): Updated line_item's own line_total: {db_line_item.line_total}")
    db.add(db_line_item)
    parent_invoice = await get_invoice(db, invoice_id=db_line_item.invoice_id)
    if not parent_invoice: raise ValueError("Parent invoice not found for line item.")
    all_line_items_data: List[InvoiceItemCreate] = []
    if parent_invoice.line_items:
        for li_orm in parent_invoice.line_items:
            all_line_items_data.append(
                 InvoiceItemCreate(
                    item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                    quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, price=li_orm.price,
                    price_per_type=li_orm.price_per_type, currency=li_orm.currency,
                    item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id
                )
            )
    print(f"DEBUG (update_li): Line items for parent recalculation: {all_line_items_data}")
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
    )
    print(f"DEBUG (update_li): Recalculated parent totals: Sub={subtotal}, Tax={tax_amt}, Disc={discount_amt}, Total={total}")
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    db.add(parent_invoice)
    await db.commit()
    await db.refresh(db_line_item); await db.refresh(parent_invoice)
    print(f"--- DEBUG: Exiting update_invoice_line_item. Line Item ID: {db_line_item.id}, Parent Total: {parent_invoice.total_amount} ---\n")
    return db_line_item

async def delete_invoice_line_item(db: AsyncSession, *, db_line_item: InvoiceItemModel) -> InvoiceItemModel:
    print(f"\n--- DEBUG: Entering delete_invoice_line_item for Line Item ID: {db_line_item.id} ---")
    parent_invoice_id = db_line_item.invoice_id
    line_item_id_to_exclude = db_line_item.id
    await db.delete(db_line_item)
    print(f"DEBUG (delete_li): Marked line item {line_item_id_to_exclude} for deletion.")
    parent_invoice = await get_invoice(db, invoice_id=parent_invoice_id)
    if not parent_invoice:
        await db.commit() 
        print(f"--- DEBUG: Exiting delete_invoice_line_item (Parent invoice not found, committed deletion of item {line_item_id_to_exclude}) ---\n")
        return db_line_item 
    all_line_items_data: List[InvoiceItemCreate] = []
    if parent_invoice.line_items:
        for li_orm in parent_invoice.line_items:
            if li_orm.id != line_item_id_to_exclude:
                all_line_items_data.append(
                    InvoiceItemCreate(
                        item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                        quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, price=li_orm.price,
                        price_per_type=li_orm.price_per_type, currency=li_orm.currency,
                        item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id
                    )
                )
    print(f"DEBUG (delete_li): Line items for parent recalculation (after excluding deleted): {all_line_items_data}")
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
    )
    print(f"DEBUG (delete_li): Recalculated parent totals: Sub={subtotal}, Tax={tax_amt}, Disc={discount_amt}, Total={total}")
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    db.add(parent_invoice)
    await db.commit()
    print(f"--- DEBUG: Exiting delete_invoice_line_item. Deleted item ID: {line_item_id_to_exclude}, Parent Total: {parent_invoice.total_amount} ---\n")
    return db_line_item


async def transform_pro_forma_to_commercial(
    db: AsyncSession, *, pro_forma_invoice: InvoiceModel, new_invoice_number: Optional[str] = None
) -> InvoiceModel:
    print(f"\n--- DEBUG: Entering transform_pro_forma_to_commercial for Pro Forma ID: {pro_forma_invoice.id} ---")
    if pro_forma_invoice.invoice_type != InvoiceTypeEnum.PRO_FORMA:
        raise ValueError("Only Pro Forma invoices can be transformed.")
    if not pro_forma_invoice.line_items: 
        print(f"DEBUG (transform): Refreshing line_items for Pro Forma ID: {pro_forma_invoice.id}")
        await db.refresh(pro_forma_invoice, attribute_names=['line_items'])
    new_line_items_create_data: List[InvoiceItemCreate] = []
    if pro_forma_invoice.line_items:
        print(f"DEBUG (transform): Copying {len(pro_forma_invoice.line_items)} line items from Pro Forma.")
        for li_orm in pro_forma_invoice.line_items:
            new_line_items_create_data.append(
                InvoiceItemCreate(
                    item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                    quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, 
                    price=li_orm.price, price_per_type=li_orm.price_per_type, 
                    currency=li_orm.currency, item_specific_comments=li_orm.item_specific_comments,
                    item_id=li_orm.item_id
                )
            )
    final_new_invoice_number = new_invoice_number or f"{pro_forma_invoice.invoice_number}-COMM"
    print(f"DEBUG (transform): New commercial invoice number will be: {final_new_invoice_number}")
    commercial_invoice_create_data = InvoiceCreate(
        invoice_number=final_new_invoice_number, invoice_date=date.today(),
        due_date=pro_forma_invoice.due_date, invoice_type=InvoiceTypeEnum.COMMERCIAL,
        status=InvoiceStatusEnum.DRAFT, currency=pro_forma_invoice.currency,
        organization_id=pro_forma_invoice.organization_id, customer_id=pro_forma_invoice.customer_id,
        tax_percentage=pro_forma_invoice.tax_percentage, discount_percentage=pro_forma_invoice.discount_percentage,
        comments_notes=pro_forma_invoice.comments_notes, line_items=new_line_items_create_data
    )
    print(f"DEBUG (transform): CommercialInvoiceCreate payload: {commercial_invoice_create_data}")
    new_commercial_invoice = await create_invoice_with_items(
        db=db, invoice_in=commercial_invoice_create_data, owner_id=pro_forma_invoice.user_id
    )
    print(f"--- DEBUG: Exiting transform_pro_forma_to_commercial. New Commercial Invoice ID: {new_commercial_invoice.id}, Total: {new_commercial_invoice.total_amount} ---\n")
    return new_commercial_invoice