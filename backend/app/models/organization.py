import uuid
from sqlalchemy import Column, String, Text, ForeignKey # ForeignKey will be used later
from sqlalchemy.dialects.postgresql import UUID # For UUID type in PostgreSQL
# from sqlalchemy.orm import relationship # Will be used for User relationship

from app.db.base_class import Base # Our custom declarative base

class Organization(Base):
    # __tablename__ will be 'organizations' due to our CustomBase

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    logo_url = Column(String(1024), nullable=True) # Store URL to logo

    # Address fields
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province_region = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Placeholder for user relationship (many organizations can belong to one user,
    # or many users to many orgs depending on future requirements.
    # For now, assuming one user owns multiple orgs)
    # user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # owner = relationship("User", back_populates="organizations")

    # Relationships to other entities (e.g., Invoices, Customers, Items)
    # invoices = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")
    # customers = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    # items = relationship("Item", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"