import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Float, Date, DateTime, Enum 
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps

from app.db.base_class import Base
from app.schemas.invoice import InvoiceTypeEnum, InvoiceStatusEnum, PricePerTypeEnum, DiscountTypeEnum # Import enums for DB

class Invoice(Base):
    # __tablename__ will be 'invoices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    invoice_number = Column(String(50), nullable=False, index=True) # Should be unique per organization
    invoice_date = Column(Date, nullable=False, default=func.current_date())
    due_date = Column(Date, nullable=True)
    
    invoice_type = Column(Enum(InvoiceTypeEnum, name='invoice_type_enum', native_enum=True, create_type=False), default=InvoiceTypeEnum.COMMERCIAL, nullable=False)
    status = Column(Enum(InvoiceStatusEnum, name='invoice_status_enum', native_enum=True, create_type=False), default=InvoiceStatusEnum.DRAFT, nullable=False)

    
    currency = Column(String(3), nullable=False, default="USD") # Overall invoice currency

    subtotal_amount = Column(Float, nullable=False, default=0.0)
    tax_percentage = Column(Float, nullable=True) # e.g., 10 for 10%
    tax_amount = Column(Float, nullable=False, default=0.0)
    tax_percentage = Column(Float, nullable=True) # e.g., 10 for 10%
    tax_amount = Column(Float, nullable=False, default=0.0)
    
    discount_type = Column(Enum(DiscountTypeEnum, name='discount_type_enum', native_enum=True, create_type=False), default=DiscountTypeEnum.PERCENTAGE, nullable=False)
    discount_percentage = Column(Float, nullable=True) # e.g., 5 for 5%
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0) # This should be calculated
    amount_paid = Column(Float, nullable=False, default=0.0)

    comments_notes = Column(Text, nullable=True)
    pdf_url = Column(String(1024), nullable=True) # URL to generated PDF

    # --- NEW OPTIONAL FIELDS for Commercial/Packing List ---
    container_number = Column(String(100), nullable=True)
    seal_number = Column(String(100), nullable=True)
    hs_code = Column(String(100), nullable=True) # Harmonized System Code
    # --- END NEW FIELDS ---

    bl_number = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True) # User who created/owns

    # Relationships
    organization = relationship("Organization") # No back_populates needed if Org doesn't list invoices directly
    customer = relationship("Customer", back_populates="invoices")
    owner = relationship("User") # User who created it

    line_items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan", # If invoice is deleted, its items are deleted
        lazy="selectin" # Eagerly load line items when an invoice is fetched
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}')>"


class InvoiceItem(Base):
    # __tablename__ will be 'invoiceitems' (or customize with __tablename__)
    __tablename__ = "invoice_items" # Explicit for clarity

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    item_description = Column(Text, nullable=False) # Can be item name or custom
    
    quantity_cartons = Column(Float, nullable=True)
    quantity_units = Column(Float, nullable=True)
    unit_type = Column(String(50), nullable=True, default="pieces")
    
    price = Column(Float, nullable=False)
    price_per_type = Column(
        Enum(   
            PricePerTypeEnum,
            name='price_per_type_enum',
            create_type=False,
            values_callable=lambda x: [e.value for e in x] # Apply to all enums
        ),
        nullable=False,
        default=PricePerTypeEnum.UNIT
    )
    currency = Column(String(3), nullable=False, default="USD")
    
    item_specific_comments = Column(Text, nullable=True)
    line_total = Column(Float, nullable=False, default=0.0) # Will be calculated

    # --- NEW FIELDS FOR PACKING LIST ---
    net_weight_kgs = Column(Float, nullable=True)
    gross_weight_kgs = Column(Float, nullable=True)
    measurement_cbm = Column(Float, nullable=True) # Cubic Meters
    # --- END NEW FIELDS ---

    # Foreign Keys
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=True, index=True) # Optional link to a predefined item

    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")
    item = relationship("Item") # No back_populates from Item to all its line items across all invoices typically

    def __repr__(self):
        return f"<InvoiceItem(id={self.id}, description='{self.item_description[:30]}...')>"