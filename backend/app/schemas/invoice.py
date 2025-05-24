from pydantic import BaseModel, Field, constr, validator, HttpUrl
from typing import Optional, List
import uuid
from datetime import date, datetime # For dates and timestamps
from enum import Enum

# --- Enums for Invoice ---
class InvoiceTypeEnum(str, Enum):
    PRO_FORMA = "Pro Forma"
    COMMERCIAL = "Commercial"

class InvoiceStatusEnum(str, Enum):
    DRAFT = "Draft"
    UNPAID = "Unpaid"
    PAID = "Paid"
    PARTIALLY_PAID = "Partially Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"

class PricePerTypeEnum(str, Enum):
    UNIT = "unit"
    CARTON = "carton"

# --- InvoiceItem Schemas ---
class InvoiceItemBase(BaseModel):
    item_description: str 
    quantity_cartons: Optional[float] = Field(default=None, ge=0)
    quantity_units: Optional[float] = Field(default=None, ge=0)
    unit_type: Optional[str] = Field(default="pieces", description="e.g., pieces, units, dozens, sets, kg, meters")
    price: float = Field(..., gt=0) 
    price_per_type: PricePerTypeEnum = PricePerTypeEnum.UNIT
    currency: str = Field(default="USD", max_length=3, min_length=3)
    item_specific_comments: Optional[str] = None
    # item_id is handled in Create/Response schemas

class InvoiceItemCreate(InvoiceItemBase):
    item_id: Optional[uuid.UUID] = None 

class InvoiceItemUpdate(BaseModel): # All fields optional for update
    item_description: Optional[str] = None
    quantity_cartons: Optional[float] = Field(default=None, ge=0, allow_none=True) # allow_none for explicit null
    quantity_units: Optional[float] = Field(default=None, ge=0, allow_none=True)
    unit_type: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0, allow_none=True)
    price_per_type: Optional[PricePerTypeEnum] = None
    currency: Optional[str] = Field(default=None, max_length=3, min_length=3, allow_none=True)
    item_specific_comments: Optional[str] = None
    item_id: Optional[uuid.UUID] = None # Allow changing/setting linked item

class InvoiceItem(InvoiceItemBase): # Response model for InvoiceItem
    id: uuid.UUID
    invoice_id: uuid.UUID 
    item_id: Optional[uuid.UUID] = None 
    line_total: float 

    class Config:
        from_attributes = True


# --- Invoice Schemas ---
class InvoiceBase(BaseModel):
    invoice_number: constr(min_length=1, max_length=50)
    invoice_date: date = Field(default_factory=date.today)
    due_date: Optional[date] = None
    invoice_type: InvoiceTypeEnum = InvoiceTypeEnum.COMMERCIAL
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT
    currency: str = Field(default="USD", max_length=3, min_length=3)
    
    subtotal_amount: Optional[float] = Field(default=0.0, ge=0)
    tax_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    tax_amount: Optional[float] = Field(default=0.0, ge=0)
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    discount_amount: Optional[float] = Field(default=0.0, ge=0)
    total_amount: Optional[float] = Field(default=0.0, ge=0)
    amount_paid: Optional[float] = Field(default=0.0, ge=0)
    
    comments_notes: Optional[str] = None
    pdf_url: Optional[HttpUrl] = None # Kept as HttpUrl here

    # --- NEW OPTIONAL FIELDS as per feedback ---
    container_number: Optional[str] = Field(default=None, max_length=100)
    seal_number: Optional[str] = Field(default=None, max_length=100)
    hs_code: Optional[str] = Field(default=None, max_length=100)
    # --- END NEW FIELDS ---

class InvoiceCreate(InvoiceBase):
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    line_items: List[InvoiceItemCreate] = []

    # Calculated fields should not be sent by client during creation; backend computes them.
    # Pydantic V2: exclude=True in model_dump, or ensure they are not required here.
    # By making them Optional[float] = None in InvoiceBase and not overriding here,
    # they won't be required in the payload unless explicitly set.
    # The exclude in model_dump in CRUD is still a good safety.
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT # Enforce draft on creation
    subtotal_amount: Optional[float] = Field(None, exclude=True) 
    tax_amount: Optional[float] = Field(None, exclude=True)
    total_amount: Optional[float] = Field(None, exclude=True)
    amount_paid: float = Field(0.0, exclude=True) # Default to 0, exclude from client input
    pdf_url: Optional[HttpUrl] = Field(None, exclude=True)
    
    # New fields (container_number, seal_number, hs_code) are inherited as optional from InvoiceBase.

    @validator('line_items', pre=True, always=True)
    def check_line_items_not_empty_if_not_draft(cls, v, values):
        # Allow draft invoices to be created without line items.
        # For other statuses, line items might be required depending on business logic.
        # This example keeps it flexible; for production, you might enforce for non-draft.
        # if values.get('status') != InvoiceStatusEnum.DRAFT and not v:
        #     raise ValueError('Invoice must have at least one line item if not a DRAFT.')
        return v


class InvoiceUpdate(BaseModel): 
    invoice_number: Optional[constr(min_length=1, max_length=50)] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_type: Optional[InvoiceTypeEnum] = None
    status: Optional[InvoiceStatusEnum] = None
    currency: Optional[str] = Field(default=None, max_length=3, min_length=3, allow_none=True)
    
    customer_id: Optional[uuid.UUID] = None 
    
    subtotal_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    tax_percentage: Optional[float] = Field(default=None, ge=0, le=100, allow_none=True)
    tax_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100, allow_none=True)
    discount_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    total_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    amount_paid: Optional[float] = Field(default=None, ge=0, allow_none=True)
    
    comments_notes: Optional[str] = None
    line_items: Optional[List[InvoiceItemCreate]] = None 
    # pdf_url is not updatable by client

    # --- NEW OPTIONAL FIELDS for update as per feedback ---
    container_number: Optional[str] = Field(default=None, max_length=100, validate_default=False)
    seal_number: Optional[str] = Field(default=None, max_length=100, validate_default=False)
    hs_code: Optional[str] = Field(default=None, max_length=100, validate_default=False)
    # --- END NEW FIELDS ---


class Invoice(InvoiceBase): # Full invoice response model
    id: uuid.UUID
    organization_id: uuid.UUID
    customer_id: uuid.UUID # Already in InvoiceBase but good to be explicit for response clarity
    line_items: List[InvoiceItem] = [] 
    created_at: datetime
    updated_at: datetime
    # container_number, seal_number, hs_code, pdf_url are inherited from InvoiceBase

    class Config:
        from_attributes = True

class InvoiceSummary(BaseModel): # For lists
    id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_company_name: Optional[str] = None 
    total_amount: float
    currency: str
    status: InvoiceStatusEnum
    invoice_type: InvoiceTypeEnum

    class Config:
        from_attributes = True