# backend/app/models/__init__.py
from .user import User
from .invoice_template import InvoiceTemplate # Should be defined before Organization
from .item import Item

from .organization import Organization # References User and InvoiceTemplate
from .customer import Customer
from .item_image import ItemImage
from .invoice import Invoice, InvoiceItem