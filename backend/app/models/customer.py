import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Customer(Base):
    # __tablename__ will be 'customers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    poc_name = Column(String(255), nullable=True)

    # Billing Address
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state_province_region = Column(String(100), nullable=True)
    billing_zip_code = Column(String(20), nullable=True)
    billing_country = Column(String(100), nullable=True)

    email = Column(String(255), nullable=True, index=True)
    phone_number = Column(String(50), nullable=True)
    # whatsapp_number = Column(String(50), nullable=True)

    # Foreign Key to Organization
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Relationship to Organization: A customer belongs to one organization
    organization = relationship("Organization", back_populates="customers")

    # Relationship to Invoices: A customer can have multiple invoices
    invoices = relationship(
        "Invoice",
        back_populates="customer",
        cascade="all, delete-orphan" # If a customer is deleted, their invoices are also deleted
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, company_name='{self.company_name}')>"