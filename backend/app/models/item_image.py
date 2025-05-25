# backend/app/models/item_image.py
import uuid
from typing import Optional
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class ItemImage(Base):
    __tablename__ = "item_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False, index=True)
    image_url = Column(String(1024), nullable=False) # Relative path to the image file
    order_index = Column(Integer, default=0) # For ordering images if needed
    alt_text: Optional[str] = Column(String(255), nullable=True) # Optional

    item = relationship("Item", back_populates="images")

    def __repr__(self):
        return f"<ItemImage(id={self.id}, item_id={self.item_id}, url='{self.image_url}')>"