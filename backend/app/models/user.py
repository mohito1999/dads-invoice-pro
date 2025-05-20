import uuid
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
      # __tablename__ will be 'users'

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
      full_name = Column(String(255), index=True, nullable=True)
      email = Column(String(255), unique=True, index=True, nullable=False)
      hashed_password = Column(String(255), nullable=False)
      is_active = Column(Boolean(), default=True)
      # is_superuser = Column(Boolean(), default=False) # For admin roles later

      # Relationship to Organization: A user can have multiple organizations
      organizations = relationship(
          "Organization",
          back_populates="owner", # Must match 'owner' in Organization model
          cascade="all, delete-orphan"
      )

      def __repr__(self):
          return f"<User(id={self.id}, email='{self.email}')>"