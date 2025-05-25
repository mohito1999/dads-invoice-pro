# backend/app/models/invoice_template.py
import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer # Removed ForeignKey as it's not used here
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship # Not used here

from app.db.base_class import Base # <<< CRITICAL: Ensure this is the correct import

class InvoiceTemplate(Base): # <<< CRITICAL: Ensure it inherits from Base
    # __tablename__ will be 'invoice_templates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    template_file_path = Column(String(255), nullable=False, unique=True)
    thumbnail_url = Column(String(1024), nullable=True)
    is_system_default = Column(Boolean, default=False, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<InvoiceTemplate(id={self.id}, name='{self.name}', path='{self.template_file_path}')>"