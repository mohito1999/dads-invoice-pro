import uuid
from sqlalchemy import Column, String, Text, ForeignKey # ForeignKey is used
from sqlalchemy.dialects.postgresql import UUID # UUID is used
from sqlalchemy.orm import relationship # relationship is used

from app.db.base_class import Base # Our custom declarative base

class Organization(Base):
    # __tablename__ will be 'organizations' due to our CustomBase
    # (Assuming your Base class handles table name generation, e.g., pluralizing the class name)

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

    # --- USER RELATIONSHIP ---
    # This links an organization to its owning user.
    # Every organization must have an owner.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", back_populates="organizations") # Must match 'organizations' in User model
    # --- END USER RELATIONSHIP ---
    # --- ADD CUSTOMERS RELATIONSHIP ---
    customers = relationship(
        "Customer",
        back_populates="organization", # Must match 'organization' in Customer model
        cascade="all, delete-orphan" # If an org is deleted, its customers are also deleted
    )
    # --- END CUSTOMERS RELATIONSHIP ---
    items = relationship(
        "Item",
        back_populates="organization", # Must match 'organization' in Item model
        cascade="all, delete-orphan" # If an org is deleted, its items are also deleted
    )

    # --- NEW: Link to InvoiceTemplate ---
    selected_invoice_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoicetemplates.id"), # <<< CORRECTED: matches 'InvoiceTemplate'.lower() + 's'
        nullable=True
    )

    selected_invoice_template = relationship(
        "InvoiceTemplate", # String reference to avoid circular import if InvoiceTemplate model also refers to Organization
        backref="organizations_using_this_template", # Optional: allows InvoiceTemplate to see which orgs use it
        lazy="selectin" # Eagerly load the selected template details when an org is fetched
    )
    # --- END NEW ---

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"