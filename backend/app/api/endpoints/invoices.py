from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
import uuid
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape # For Jinja2
from weasyprint import HTML # For WeasyPrint
from pathlib import Path # For path manipulation

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps # For get_current_active_user and get_valid_organization_for_user

router = APIRouter()

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" # backend/app/templates
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)


@router.post("/", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
async def create_new_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_in: schemas.InvoiceCreate, # Contains organization_id, customer_id, line_items
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create a new invoice with its line items.
    The invoice is associated with the current authenticated user.
    """
    # 1. Authorize that the current user owns the target organization
    organization = await deps.get_valid_organization_for_user(
        db=db, org_id=invoice_in.organization_id, current_user=current_user
    )

    # 2. Validate the customer belongs to this organization
    customer = await crud.customer.get_customer(db, customer_id=invoice_in.customer_id)
    if not customer or customer.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer not found or does not belong to the specified organization."
        )
    
    # 3. Optional: Validate items if item_id is provided in line_items
    for line_item_in in invoice_in.line_items:
        if line_item_in.item_id:
            item = await crud.item.get_item(db, item_id=line_item_in.item_id)
            if not item or item.organization_id != organization.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item with ID {line_item_in.item_id} not found or does not belong to the organization."
                )
    
    invoice = await crud.invoice.create_invoice_with_items(
        db=db, invoice_in=invoice_in, owner_id=current_user.id
    )
    return invoice

@router.get("/", response_model=List[schemas.InvoiceSummary])
async def read_invoices_for_user(
    *,
    db: AsyncSession = Depends(get_db),
    organization_id: Optional[uuid.UUID] = Query(None, description="Filter by organization ID"),
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter by customer ID"),
    status: Optional[schemas.InvoiceStatusEnum] = Query(None, description="Filter by invoice status"),
    invoice_number_search: Optional[str] = Query(None, description="Search by invoice number (partial match)"),
    date_from: Optional[date] = Query(None, description="Filter invoices from this date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter invoices up to this date (YYYY-MM-DD)"),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve invoices for the current authenticated user, with optional filters.
    If organization_id is provided, authorization for that org is checked.
    """
    if organization_id:
        # Ensure user has access to this organization if specified for filtering
        await deps.get_valid_organization_for_user(db=db, org_id=organization_id, current_user=current_user)

    invoices = await crud.invoice.get_invoices_by_user(
        db,
        user_id=current_user.id,
        organization_id=organization_id,
        status=status,
        customer_id=customer_id,
        invoice_number_search=invoice_number_search,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit
    )
    
    # Prepare summary response, including customer company name
    summaries = []
    for inv in invoices:
        # inv.customer should be loaded by joinedload in crud.get_invoices_by_user
        customer_name = inv.customer.company_name if inv.customer else None
        summaries.append(
            schemas.InvoiceSummary(
                id=inv.id,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                customer_company_name=customer_name,
                total_amount=inv.total_amount,
                currency=inv.currency,
                status=inv.status,
                invoice_type=inv.invoice_type
            )
        )
    return summaries


@router.get("/{invoice_id}", response_model=schemas.Invoice)
async def read_invoice_by_id(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a specific invoice by ID. Ensures the invoice belongs to the current user.
    """
    invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id) # get_invoice eager loads items
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    return invoice

@router.put("/{invoice_id}", response_model=schemas.Invoice)
async def update_existing_invoice(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    invoice_in: schemas.InvoiceUpdate, # Now includes optional line_items
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update an invoice. Ensures the invoice belongs to the current user.
    If 'line_items' are provided in the payload, they replace existing ones.
    """
    db_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id) # Eager loads current items
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # If customer_id is being changed, validate the new customer
    if invoice_in.customer_id and invoice_in.customer_id != db_invoice.customer_id:
        new_customer = await crud.customer.get_customer(db, customer_id=invoice_in.customer_id)
        if not new_customer or new_customer.organization_id != db_invoice.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New customer not found or does not belong to the invoice's organization."
            )
    
    # If new line items are provided, validate their item_ids (if any)
    if invoice_in.line_items is not None: # Check for explicit list, even if empty
        for line_item_in_payload in invoice_in.line_items:
            if line_item_in_payload.item_id:
                item = await crud.item.get_item(db, item_id=line_item_in_payload.item_id)
                if not item or item.organization_id != db_invoice.organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Item with ID {line_item_in_payload.item_id} for new line items not found or does not belong to the organization."
                    )

    updated_invoice = await crud.invoice.update_invoice_with_items(
        db=db, 
        db_invoice=db_invoice, 
        invoice_in=invoice_in,
        new_line_items_data=invoice_in.line_items # Pass line_items if present in payload
    )
    return updated_invoice

@router.delete("/{invoice_id}", response_model=schemas.Invoice)
async def delete_existing_invoice(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete an invoice. Ensures the invoice belongs to the current user.
    """
    db_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    deleted_invoice_data = await crud.invoice.delete_invoice(db=db, db_invoice=db_invoice)
    return deleted_invoice_data

@router.get("/{invoice_id}/pdf", response_class=Response) # Use plain Response for custom media type
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Response:
    """
    Download a specific invoice as a PDF.
    Ensures the invoice belongs to the current user.
    """
    invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id) # get_invoice eager loads items, customer, org
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.user_id != current_user.id: # Authorization check
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Ensure organization is loaded if not already by get_invoice (it should be via relationships)
    # If invoice.organization is not loaded, you might need to explicitly load it or ensure your
    # get_invoice function loads it via joinedload or selectinload.
    # For this template, we assume invoice.organization and invoice.customer are loaded.
    if not invoice.organization:
         await db.refresh(invoice, attribute_names=['organization'])
    if not invoice.customer:
         await db.refresh(invoice, attribute_names=['customer'])


    # Render the HTML template with invoice data
    try:
        template = jinja_env.get_template("invoice_template.html")
        html_content = template.render(invoice=invoice)
    except Exception as e:
        print(f"Error rendering template: {e}") # Log this
        raise HTTPException(status_code=500, detail="Error generating invoice: Template rendering failed.")

    # Generate PDF using WeasyPrint
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        # WeasyPrint can raise various errors, e.g., if CSS is bad or dependencies missing
        print(f"Error generating PDF with WeasyPrint: {e}") # Log this
        raise HTTPException(status_code=500, detail=f"Error generating invoice: PDF conversion failed. Details: {str(e)}")

    # Return PDF as a response
    filename = f"Invoice-{invoice.invoice_number.replace('/', '-')}.pdf" # Sanitize filename
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
        # Use "inline" instead of "attachment" if you want browser to display it directly
    )

@router.post("/{invoice_id}/transform-to-commercial", response_model=schemas.Invoice)
async def transform_invoice_to_commercial(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    # Optionally allow providing a new invoice number for the commercial version
    new_invoice_number: Optional[str] = Query(None, description="Optional new invoice number for the commercial invoice.")
) -> Any:
    """
    Transforms a Pro Forma invoice into a new Commercial invoice.
    The original Pro Forma invoice remains unchanged.
    """
    pro_forma_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not pro_forma_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pro Forma Invoice not found")
    if pro_forma_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions for this invoice")
    if pro_forma_invoice.invoice_type != schemas.InvoiceTypeEnum.PRO_FORMA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Pro Forma invoices can be transformed."
        )

    try:
        commercial_invoice = await crud.invoice.transform_pro_forma_to_commercial(
            db=db,
            pro_forma_invoice=pro_forma_invoice,
            new_invoice_number=new_invoice_number
        )
    except ValueError as e: # Catch specific errors from CRUD if any
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    return commercial_invoice