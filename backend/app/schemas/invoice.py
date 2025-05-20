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
    CANCELLED = "Cancelled" # Adding Cancelled as a common status

class PricePerTypeEnum(str, Enum):
    UNIT = "unit"
    CARTON = "carton"

# --- InvoiceItem Schemas ---
class InvoiceItemBase(BaseModel):
    item_description: str # Could be item name or a custom description
    quantity_cartons: Optional[float] = Field(default=None, ge=0)
    quantity_units: Optional[float] = Field(default=None, ge=0)
    unit_type: Optional[str] = Field(default="pieces", description="e.g., pieces, units, dozens, sets, kg, meters")
    price: float = Field(..., gt=0) # Price must be positive
    price_per_type: PricePerTypeEnum = PricePerTypeEnum.UNIT
    currency: str = Field(default="USD", max_length=3, min_length=3) # Default currency, ISO 3-letter code
    item_specific_comments: Optional[str] = None
    # item_id: Optional[uuid.UUID] = None # Link to a predefined item, if applicable

class InvoiceItemCreate(InvoiceItemBase):
    item_id: Optional[uuid.UUID] = None # Allow linking to an existing item

class InvoiceItemUpdate(InvoiceItemBase): # All fields optional for update
    item_description: Optional[str] = None
    quantity_cartons: Optional[float] = Field(default=None, ge=0, allow_none=True)
    quantity_units: Optional[float] = Field(default=None, ge=0, allow_none=True)
    unit_type: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0, allow_none=True)
    price_per_type: Optional[PricePerTypeEnum] = None
    currency: Optional[str] = Field(default=None, max_length=3, min_length=3, allow_none=True)
    item_specific_comments: Optional[str] = None
    item_id: Optional[uuid.UUID] = None


class InvoiceItem(InvoiceItemBase): # Response model for InvoiceItem
    id: uuid.UUID
    invoice_id: uuid.UUID # Link back to invoice
    item_id: Optional[uuid.UUID] = None # Link to a predefined item
    line_total: float # Calculated field

    class Config:
        from_attributes = True


# --- Invoice Schemas ---
class InvoiceBase(BaseModel):
    invoice_number: constr(min_length=1, max_length=50)
    invoice_date: date = Field(default_factory=date.today)
    due_date: Optional[date] = None
    invoice_type: InvoiceTypeEnum = InvoiceTypeEnum.COMMERCIAL
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT
    currency: str = Field(default="USD", max_length=3, min_length=3) # Overall invoice currency
    
    # Financials - these will often be calculated but can be overridden if needed
    subtotal_amount: Optional[float] = Field(default=0.0, ge=0)
    tax_percentage: Optional[float] = Field(default=None, ge=0, le=100) # Percentage
    tax_amount: Optional[float] = Field(default=0.0, ge=0)
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100) # Percentage
    discount_amount: Optional[float] = Field(default=0.0, ge=0)
    total_amount: Optional[float] = Field(default=0.0, ge=0)
    amount_paid: Optional[float] = Field(default=0.0, ge=0)
    
    comments_notes: Optional[str] = None # General comments for the whole invoice
    pdf_url: Optional[HttpUrl] = None # URL to the generated PDF

class InvoiceCreate(InvoiceBase):
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    line_items: List[InvoiceItemCreate] = [] # List of items to be created with the invoice

    # Remove fields that should be auto-calculated or set by system
    # status: Optional[InvoiceStatusEnum] = InvoiceStatusEnum.DRAFT # Enforce draft on creation via API
    subtotal_amount: Optional[float] = None # Will be calculated
    tax_amount: Optional[float] = None      # Will be calculated (or derived if percentage given)
    total_amount: Optional[float] = None    # Will be calculated
    pdf_url: Optional[HttpUrl] = None       # Will be set by system

    @validator('line_items', pre=True, always=True)
    def check_line_items_not_empty(cls, v):
        # if not v: # Allow creating draft invoices without line items initially
        #     raise ValueError('Invoice must have at least one line item')
        return v


class InvoiceUpdate(BaseModel): # Highly flexible update
    invoice_number: Optional[constr(min_length=1, max_length=50)] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_type: Optional[InvoiceTypeEnum] = None
    status: Optional[InvoiceStatusEnum] = None
    currency: Optional[str] = Field(default=None, max_length=3, min_length=3, allow_none=True)
    
    customer_id: Optional[uuid.UUID] = None # Allow changing customer (carefully)
    
    subtotal_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    tax_percentage: Optional[float] = Field(default=None, ge=0, le=100, allow_none=True)
    tax_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    discount_percentage: Optional[float] = Field(default=None, ge=0, le=100, allow_none=True)
    discount_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    total_amount: Optional[float] = Field(default=None, ge=0, allow_none=True)
    amount_paid: Optional[float] = Field(default=None, ge=0, allow_none=True)
    
    comments_notes: Optional[str] = None
    line_items: Optional[List[InvoiceItemCreate]] = None 
    # pdf_url should not be updated directly by client
    # line_items are typically managed via separate endpoints or a full replacement list.
    # For simplicity, we might allow full replacement if needed, or dedicated line item endpoints.


class Invoice(InvoiceBase): # Full invoice response model
    id: uuid.UUID
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    line_items: List[InvoiceItem] = [] # Include fully populated line items
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InvoiceSummary(BaseModel): # For lists
    id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_company_name: Optional[str] = None # Denormalized for easy display
    total_amount: float
    currency: str
    status: InvoiceStatusEnum
    invoice_type: InvoiceTypeEnum

    class Config:
        from_attributes = True