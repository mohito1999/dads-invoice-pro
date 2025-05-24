from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, or_
import uuid
from datetime import date, datetime
from typing import Optional

from app.models.invoice import Invoice as InvoiceModel
from app.schemas.invoice import InvoiceStatusEnum # For filtering by status
# from app.models.organization import Organization as OrganizationModel # If fetching org currency

async def get_dashboard_stats(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
) -> dict: # Returns a dictionary that can be validated by DashboardStats schema
    
    # Base query for invoices belonging to the user
    query_filters = [InvoiceModel.user_id == user_id]

    if organization_id:
        query_filters.append(InvoiceModel.organization_id == organization_id)
    
    # Date filtering
    # If only date_from, then from that date onwards
    # If only date_to, then up to that date
    # If both, then within the range
    if date_from:
        query_filters.append(InvoiceModel.invoice_date >= date_from)
    if date_to:
        query_filters.append(InvoiceModel.invoice_date <= date_to)

    # --- Total Invoiced Amount ---
    # Sum total_amount of all non-cancelled, non-draft invoices (or all if preferred)
    # For simplicity, let's sum all non-cancelled. Drafts might be excluded by some.
    total_invoiced_query = select(func.sum(InvoiceModel.total_amount)).filter(
        and_(*query_filters, InvoiceModel.status != InvoiceStatusEnum.CANCELLED)
        # Optional: .filter(InvoiceModel.status != InvoiceStatusEnum.DRAFT)
    )
    total_invoiced_result = await db.execute(total_invoiced_query)
    total_invoiced_amount = total_invoiced_result.scalar_one_or_none() or 0.0

    # --- Total Collected Amount ---
    # Sum amount_paid of 'Paid' and 'Partially Paid' invoices
    # OR just sum amount_paid for all non-cancelled invoices
    total_collected_query = select(func.sum(InvoiceModel.amount_paid)).filter(
        and_(*query_filters, InvoiceModel.status != InvoiceStatusEnum.CANCELLED)
    )
    total_collected_result = await db.execute(total_collected_query)
    total_collected_amount = total_collected_result.scalar_one_or_none() or 0.0

    # --- Total Outstanding Amount ---
    # This could be total_invoiced - total_collected
    # Or, sum of (total_amount - amount_paid) for Unpaid, Partially Paid, Overdue
    # total_outstanding_amount = total_invoiced_amount - total_collected_amount
    # Let's do the sum for more precision if totals were ever manually overridden
    outstanding_query = select(func.sum(InvoiceModel.total_amount - InvoiceModel.amount_paid)).filter(
        and_(
            *query_filters,
            InvoiceModel.status.in_([
                InvoiceStatusEnum.UNPAID,
                InvoiceStatusEnum.PARTIALLY_PAID,
                InvoiceStatusEnum.OVERDUE
            ])
        )
    )
    outstanding_result = await db.execute(outstanding_query)
    total_outstanding_amount = outstanding_result.scalar_one_or_none() or 0.0


    # --- Count of Overdue Invoices ---
    # Overdue status OR (Unpaid/Partially Paid AND due_date < today)
    # For simplicity here, just count by status. A more robust check would use due_date.
    # Make sure due_date is not None for overdue calculation if based on date.
    today = date.today()
    overdue_count_query = select(func.count(InvoiceModel.id)).filter(
        and_(
            *query_filters,
            or_(
                InvoiceModel.status == InvoiceStatusEnum.OVERDUE,
                and_(
                    InvoiceModel.status.in_([InvoiceStatusEnum.UNPAID, InvoiceStatusEnum.PARTIALLY_PAID]),
                    InvoiceModel.due_date != None, # mypy/linter might need != None explicitly
                    InvoiceModel.due_date < today 
                )
            )
        )
    )
    overdue_count_result = await db.execute(overdue_count_query)
    count_overdue_invoices = overdue_count_result.scalar_one() or 0

    # Currency: For V1, if an organization is selected, we could try to fetch its default currency.
    # If no org selected, or orgs have different currencies, this becomes complex.
    # For now, let's return None, implying the frontend might need to specify or assume.
    # Or, if all amounts are from a single currency DB column, we can fetch one invoice's currency.
    default_currency = "USD" # Fallback
    if organization_id:
        # Fetch one invoice from this org to get its currency as representative
        # This is a simplification. Ideally, Org model would have a default currency.
        first_invoice_for_org_query = select(InvoiceModel.currency).filter(
            InvoiceModel.organization_id == organization_id
        ).limit(1)
        currency_result = await db.execute(first_invoice_for_org_query)
        org_currency = currency_result.scalar_one_or_none()
        if org_currency:
            default_currency = org_currency
    elif user_id and not organization_id: # If no specific org, try to get from any user invoice
        first_invoice_for_user_query = select(InvoiceModel.currency).filter(
            InvoiceModel.user_id == user_id
        ).limit(1)
        currency_result = await db.execute(first_invoice_for_user_query)
        user_currency = currency_result.scalar_one_or_none()
        if user_currency:
            default_currency = user_currency


    return {
        "total_invoiced_amount": round(total_invoiced_amount, 2),
        "total_collected_amount": round(total_collected_amount, 2),
        "total_outstanding_amount": round(total_outstanding_amount, 2),
        "count_overdue_invoices": count_overdue_invoices,
        "currency": default_currency # V1: simplified currency handling
    }