from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import declared_attr
from typing import Any

class CustomBase:
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"

Base: Any = declarative_base(cls=CustomBase)