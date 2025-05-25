# backend/app/crud/crud_invoice.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
import uuid
from datetime import date
from typing import List, Tuple, Optional 

from app.models.invoice import Invoice as InvoiceModel, InvoiceItem as InvoiceItemModel
from app.models.item import Item as ItemModel
from app.models.customer import Customer as CustomerModel
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceStatusEnum,
    PricePerTypeEnum, 
    InvoiceItemUpdate,
    InvoiceTypeEnum,
    PaymentRecordIn
)

# Helper function to calculate a single line item's total
def _calculate_line_item_total(item_data: InvoiceItemCreate) -> float:
    """Helper to calculate a single line item's total."""
    price = item_data.price or 0.0 
    quantity = 0.0 

    if item_data.price_per_type == PricePerTypeEnum.CARTON:
        if item_data.quantity_cartons is not None:
            quantity = float(item_data.quantity_cartons)
        elif item_data.quantity_units is not None: 
            # print(f"    WARNING (_calculate_line_item_total): Price per CARTON but only quantity_units provided. Using quantity_units: {item_data.quantity_units}")
            quantity = float(item_data.quantity_units)
    elif item_data.price_per_type == PricePerTypeEnum.UNIT:
        if item_data.quantity_units is not None:
            quantity = float(item_data.quantity_units)
        elif item_data.quantity_cartons is not None: 
            # print(f"    WARNING (_calculate_line_item_total): Price per UNIT but only quantity_cartons provided. Using quantity_cartons: {item_data.quantity_cartons}")
            quantity = float(item_data.quantity_cartons)
    else: 
        if item_data.quantity_units is not None:
            quantity = float(item_data.quantity_units)
        elif item_data.quantity_cartons is not None:
             quantity = float(item_data.quantity_cartons)

    final_price = float(price) 
    calculated_total = round(final_price * quantity, 2)
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
    subtotal = 0.0
    for item_data in line_items_data:
        line_total = _calculate_line_item_total(item_data)
        subtotal += line_total
    
    subtotal = round(subtotal, 2) 

    calculated_tax_amount = 0.0
    if tax_percentage is not None and tax_percentage > 0:
        calculated_tax_amount = round(subtotal * (tax_percentage / 100.0), 2)

    calculated_discount_amount = 0.0
    if discount_percentage is not None and discount_percentage > 0:
        calculated_discount_amount = round(subtotal * (discount_percentage / 100.0), 2)
    
    calculated_discount_amount = min(calculated_discount_amount, subtotal) 

    total = round(subtotal + calculated_tax_amount - calculated_discount_amount, 2)
    return subtotal, calculated_tax_amount, calculated_discount_amount, total


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Optional[InvoiceModel]:
    """
    Get a single invoice by its ID, eagerly loading related data for detail views and PDF.
    """
    # print(f"DEBUG (crud_invoice.get_invoice): Fetching invoice ID {invoice_id} with deep eager loading.") # Optional: keep if useful
    result = await db.execute(
        select(InvoiceModel)
        .options(
            joinedload(InvoiceModel.organization), 
            joinedload(InvoiceModel.customer),   
            selectinload(InvoiceModel.line_items) 
            .selectinload(InvoiceItemModel.item)  
            .selectinload(ItemModel.images)       
        )
        .filter(InvoiceModel.id == invoice_id)
    )
    invoice = result.scalars().first()
    # Removed extensive print block for brevity in production
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
        **invoice_data_dict, user_id=owner_id, subtotal_amount=subtotal,
        tax_amount=tax_amt if invoice_in.tax_percentage is not None else (invoice_in.tax_amount or 0.0),
        discount_amount=discount_amt if invoice_in.discount_percentage is not None else (invoice_in.discount_amount or 0.0),
        total_amount=total, status=final_status
    )
    db.add(db_invoice)
    for item_data_schema in invoice_in.line_items:
        item_line_db_total = _calculate_line_item_total(item_data_schema) 
        db_item_data = item_data_schema.model_dump()
        db_item = InvoiceItemModel(**db_item_data, line_total=item_line_db_total)
        db_item.invoice = db_invoice 
        db.add(db_item)
    await db.commit()
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None: raise Exception("Failed to retrieve created invoice after commit.")
    return refreshed_invoice


async def update_invoice_with_items(
    db: AsyncSession, *, db_invoice: InvoiceModel, invoice_in: InvoiceUpdate
) -> InvoiceModel:
    if 'line_items' in invoice_in.model_fields_set:
        await db.refresh(db_invoice, attribute_names=['line_items'])

    update_data_header = invoice_in.model_dump(exclude_unset=True, exclude={'line_items'})
    original_status = db_invoice.status

    for field, value in update_data_header.items():
        if field not in ["amount_paid", "status"]:
            setattr(db_invoice, field, value)

    line_items_for_calculation: List[InvoiceItemCreate]

    if 'line_items' in invoice_in.model_fields_set and invoice_in.line_items is not None:
        db_invoice.line_items.clear() 
        new_orm_line_items = []
        for item_data_schema in invoice_in.line_items:
            item_line_total = _calculate_line_item_total(item_data_schema)
            db_item_data_dict = item_data_schema.model_dump()
            new_db_item = InvoiceItemModel(**db_item_data_dict, line_total=item_line_total)
            new_orm_line_items.append(new_db_item)
        db_invoice.line_items = new_orm_line_items
        line_items_for_calculation = list(invoice_in.line_items)
    else:
        if not db_invoice.line_items or not all(isinstance(li, InvoiceItemModel) for li in db_invoice.line_items):
            await db.refresh(db_invoice, attribute_names=['line_items'])
        line_items_for_calculation = []
        for orm_item in db_invoice.line_items:
            line_items_for_calculation.append(
                InvoiceItemCreate(
                    item_description=orm_item.item_description,
                    quantity_cartons=orm_item.quantity_cartons,
                    quantity_units=orm_item.quantity_units,
                    unit_type=orm_item.unit_type,
                    price=orm_item.price,
                    price_per_type=orm_item.price_per_type,
                    currency=orm_item.currency,
                    item_specific_comments=orm_item.item_specific_comments,
                    item_id=orm_item.item_id,
                    net_weight_kgs=orm_item.net_weight_kgs,
                    gross_weight_kgs=orm_item.gross_weight_kgs,
                    measurement_cbm=orm_item.measurement_cbm
                )
            )
    
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=line_items_for_calculation, 
        invoice_currency=db_invoice.currency,
        tax_percentage=db_invoice.tax_percentage,
        discount_percentage=db_invoice.discount_percentage
    )
    
    db_invoice.subtotal_amount = subtotal
    db_invoice.tax_amount = tax_amt if db_invoice.tax_percentage is not None else (update_data_header.get('tax_amount', db_invoice.tax_amount))
    db_invoice.discount_amount = discount_amt if db_invoice.discount_percentage is not None else (update_data_header.get('discount_amount', db_invoice.discount_amount))
    db_invoice.total_amount = total

    requested_amount_paid = update_data_header.get("amount_paid") 
    requested_status = update_data_header.get("status")

    if requested_status is not None:
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
    
    if requested_amount_paid is not None:
        db_invoice.amount_paid = requested_amount_paid
        if requested_status is None:
            if db_invoice.amount_paid >= db_invoice.total_amount and db_invoice.total_amount > 0:
                db_invoice.status = InvoiceStatusEnum.PAID
            elif db_invoice.amount_paid > 0 and db_invoice.amount_paid < db_invoice.total_amount:
                db_invoice.status = InvoiceStatusEnum.PARTIALLY_PAID
            elif db_invoice.amount_paid <= 0:
                if db_invoice.status not in [InvoiceStatusEnum.DRAFT, InvoiceStatusEnum.CANCELLED]:
                    db_invoice.status = InvoiceStatusEnum.UNPAID
    
    db.add(db_invoice)
    await db.commit()
    
    refreshed_invoice = await get_invoice(db, invoice_id=db_invoice.id)
    if refreshed_invoice is None:
        raise Exception(f"Failed to retrieve updated invoice (ID: {db_invoice.id}) after commit.")
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
                    item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id,
                    net_weight_kgs=li_orm.net_weight_kgs, gross_weight_kgs=li_orm.gross_weight_kgs,
                    measurement_cbm=li_orm.measurement_cbm
                )
            )
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
    )
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    db.add(parent_invoice)
    await db.commit()
    await db.refresh(db_item); await db.refresh(parent_invoice)
    return db_item

async def update_invoice_line_item(
    db: AsyncSession, *, db_line_item: InvoiceItemModel, item_in: InvoiceItemUpdate
) -> InvoiceItemModel:
    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items(): setattr(db_line_item, field, value)
    temp_item_for_calc = InvoiceItemCreate(
        item_description=db_line_item.item_description, quantity_cartons=db_line_item.quantity_cartons,
        quantity_units=db_line_item.quantity_units, unit_type=db_line_item.unit_type, price=db_line_item.price,
        price_per_type=db_line_item.price_per_type, currency=db_line_item.currency,
        item_specific_comments=db_line_item.item_specific_comments, item_id=db_line_item.item_id,
        net_weight_kgs=db_line_item.net_weight_kgs, gross_weight_kgs=db_line_item.gross_weight_kgs,
        measurement_cbm=db_line_item.measurement_cbm
    )
    db_line_item.line_total = _calculate_line_item_total(temp_item_for_calc)
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
                    item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id,
                    net_weight_kgs=li_orm.net_weight_kgs, gross_weight_kgs=li_orm.gross_weight_kgs,
                    measurement_cbm=li_orm.measurement_cbm
                )
            )
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
    )
    parent_invoice.subtotal_amount = subtotal
    parent_invoice.tax_amount = tax_amt
    parent_invoice.discount_amount = discount_amt
    parent_invoice.total_amount = total
    db.add(parent_invoice)
    await db.commit()
    await db.refresh(db_line_item); await db.refresh(parent_invoice)
    return db_line_item

async def delete_invoice_line_item(db: AsyncSession, *, db_line_item: InvoiceItemModel) -> InvoiceItemModel:
    parent_invoice_id = db_line_item.invoice_id
    await db.delete(db_line_item)
    
    parent_invoice = await get_invoice(db, invoice_id=parent_invoice_id) 
    if not parent_invoice:
        await db.commit() 
        return db_line_item 
        
    all_line_items_data: List[InvoiceItemCreate] = []
    if parent_invoice.line_items: 
        for li_orm in parent_invoice.line_items:
            all_line_items_data.append(
                InvoiceItemCreate(
                    item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                    quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, price=li_orm.price,
                    price_per_type=li_orm.price_per_type, currency=li_orm.currency,
                    item_specific_comments=li_orm.item_specific_comments, item_id=li_orm.item_id,
                    net_weight_kgs=li_orm.net_weight_kgs, gross_weight_kgs=li_orm.gross_weight_kgs,
                    measurement_cbm=li_orm.measurement_cbm
                )
            )
    subtotal, tax_amt, discount_amt, total = calculate_invoice_financials(
        line_items_data=all_line_items_data, invoice_currency=parent_invoice.currency,
        tax_percentage=parent_invoice.tax_percentage, discount_percentage=parent_invoice.discount_percentage
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
    if pro_forma_invoice.invoice_type != InvoiceTypeEnum.PRO_FORMA:
        raise ValueError("Only Pro Forma invoices can be transformed.")
    
    fully_loaded_pro_forma = await get_invoice(db, invoice_id=pro_forma_invoice.id)
    if not fully_loaded_pro_forma: 
        raise ValueError("Pro Forma invoice not found for transformation.")

    new_line_items_create_data: List[InvoiceItemCreate] = []
    if fully_loaded_pro_forma.line_items:
        for li_orm in fully_loaded_pro_forma.line_items:
            new_line_items_create_data.append(
                InvoiceItemCreate(
                    item_description=li_orm.item_description, quantity_cartons=li_orm.quantity_cartons,
                    quantity_units=li_orm.quantity_units, unit_type=li_orm.unit_type, 
                    price=li_orm.price, price_per_type=li_orm.price_per_type, 
                    currency=li_orm.currency, item_specific_comments=li_orm.item_specific_comments,
                    item_id=li_orm.item_id,
                    net_weight_kgs=li_orm.net_weight_kgs, gross_weight_kgs=li_orm.gross_weight_kgs,
                    measurement_cbm=li_orm.measurement_cbm
                )
            )
    final_new_invoice_number = new_invoice_number or f"{fully_loaded_pro_forma.invoice_number}-COMM"
    commercial_invoice_create_data = InvoiceCreate(
        invoice_number=final_new_invoice_number, invoice_date=date.today(),
        due_date=fully_loaded_pro_forma.due_date, invoice_type=InvoiceTypeEnum.COMMERCIAL,
        status=InvoiceStatusEnum.DRAFT, currency=fully_loaded_pro_forma.currency,
        organization_id=fully_loaded_pro_forma.organization_id, customer_id=fully_loaded_pro_forma.customer_id,
        tax_percentage=fully_loaded_pro_forma.tax_percentage, discount_percentage=fully_loaded_pro_forma.discount_percentage,
        comments_notes=fully_loaded_pro_forma.comments_notes, 
        container_number=fully_loaded_pro_forma.container_number,
        seal_number=fully_loaded_pro_forma.seal_number,
        hs_code=fully_loaded_pro_forma.hs_code,
        bl_number=fully_loaded_pro_forma.bl_number,
        line_items=new_line_items_create_data
    )
    new_commercial_invoice = await create_invoice_with_items(
        db=db, invoice_in=commercial_invoice_create_data, owner_id=fully_loaded_pro_forma.user_id
    )
    return new_commercial_invoice


async def create_packing_list_from_commercial(
      db: AsyncSession, *, commercial_invoice: InvoiceModel, new_packing_list_number: Optional[str] = None
  ) -> InvoiceModel:
      if commercial_invoice.invoice_type != InvoiceTypeEnum.COMMERCIAL:
          raise ValueError("Only Commercial invoices can be used to generate a Packing List.")

      fully_loaded_commercial_invoice = await get_invoice(db, invoice_id=commercial_invoice.id)
      if not fully_loaded_commercial_invoice:
          raise ValueError("Commercial invoice not found for generating packing list.")

      new_line_items_data: List[InvoiceItemCreate] = []
      if fully_loaded_commercial_invoice.line_items:
          for li_orm in fully_loaded_commercial_invoice.line_items:
              new_line_items_data.append(
                  InvoiceItemCreate(
                      item_description=li_orm.item_description,
                      quantity_cartons=li_orm.quantity_cartons,
                      quantity_units=li_orm.quantity_units,
                      unit_type=li_orm.unit_type,
                      price=0, 
                      price_per_type=li_orm.price_per_type, 
                      currency=li_orm.currency, 
                      item_specific_comments=li_orm.item_specific_comments,
                      item_id=li_orm.item_id,
                      net_weight_kgs=li_orm.net_weight_kgs,
                      gross_weight_kgs=li_orm.gross_weight_kgs,
                      measurement_cbm=li_orm.measurement_cbm
                  )
              )
      
      final_packing_list_number = new_packing_list_number or f"PL-{fully_loaded_commercial_invoice.invoice_number}"

      packing_list_create_payload = InvoiceCreate(
          invoice_number=final_packing_list_number,
          invoice_date=date.today(), 
          invoice_type=InvoiceTypeEnum.PACKING_LIST,
          status=InvoiceStatusEnum.DRAFT, 
          currency=fully_loaded_commercial_invoice.currency, 
          organization_id=fully_loaded_commercial_invoice.organization_id,
          customer_id=fully_loaded_commercial_invoice.customer_id,
          subtotal_amount=0, tax_percentage=0, tax_amount=0,
          discount_percentage=0, discount_amount=0, total_amount=0, amount_paid=0,
          container_number=fully_loaded_commercial_invoice.container_number,
          seal_number=fully_loaded_commercial_invoice.seal_number,
          hs_code=fully_loaded_commercial_invoice.hs_code,
          bl_number=fully_loaded_commercial_invoice.bl_number,
          comments_notes=fully_loaded_commercial_invoice.comments_notes,
          line_items=new_line_items_data
      )

      new_packing_list_invoice = await create_invoice_with_items(
          db=db,
          invoice_in=packing_list_create_payload,
          owner_id=fully_loaded_commercial_invoice.user_id
      )
      return new_packing_list_invoice


async def record_payment_for_invoice(
    db: AsyncSession,
    *,
    db_invoice: InvoiceModel, 
    payment_in: PaymentRecordIn
) -> InvoiceModel:
    current_amount_paid_on_invoice = db_invoice.amount_paid if db_invoice.amount_paid is not None else 0.0
    new_total_amount_paid = round(current_amount_paid_on_invoice + payment_in.amount_paid_now, 2)
    
    db_invoice.amount_paid = new_total_amount_paid

    if abs(db_invoice.amount_paid - db_invoice.total_amount) < 0.01 and db_invoice.total_amount > 0: 
        db_invoice.status = InvoiceStatusEnum.PAID
        db_invoice.amount_paid = db_invoice.total_amount 
    elif db_invoice.amount_paid > 0 and db_invoice.amount_paid < db_invoice.total_amount:
        db_invoice.status = InvoiceStatusEnum.PARTIALLY_PAID
    elif db_invoice.amount_paid <= 0: 
        if db_invoice.status not in [InvoiceStatusEnum.DRAFT, InvoiceStatusEnum.CANCELLED]:
            db_invoice.status = InvoiceStatusEnum.UNPAID
    
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice) 
    return db_invoice