from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid
class DashboardStats(BaseModel):
    total_invoiced_amount: float
    total_collected_amount: float
    total_outstanding_amount: float
    count_overdue_invoices: int
    currency: Optional[str] = None # To indicate the currency of the amounts if uniform
    # We might need to handle multiple currencies later if orgs use different ones widely

class DashboardFilters(BaseModel): # For request query parameters validation by FastAPI
    organization_id: Optional[uuid.UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    # currency: Optional[str] = None # If we want to filter stats for a specific currency