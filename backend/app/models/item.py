import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Item(Base):
    # __tablename__ will be 'items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    default_price = Column(Float, nullable=True) # Check constraint for > 0 can be added at DB level if needed
    default_unit = Column(String(50), nullable=True) # e.g., "piece", "carton", "kg"
    
    # For handling multiple images, a JSONB column is flexible.
    # Or a separate ItemImage table for a more structured approach.
    # Let's use a single image_url text field for now for simplicity, matching the schema.
    image_url = Column(String(1024), nullable=True) # URL to a primary image

    # Foreign Key to Organization
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Relationship to Organization: An item belongs to one organization
    organization = relationship("Organization", back_populates="items")
    

    # Relationship to InvoiceItems: An item can be part of many invoice line items
    # We'll define InvoiceItem model later. It will link back here.
    # invoice_line_items = relationship("InvoiceItem", back_populates="item")

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}')>"