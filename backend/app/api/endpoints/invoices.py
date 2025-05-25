# backend/app/api/endpoints/invoices.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
import asyncio 
from concurrent.futures import ThreadPoolExecutor 
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
import uuid
from datetime import date
from app.core.config import settings 

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML # type: ignore
from pathlib import Path

from app import crud, models, schemas
from app.db.session import get_db
from app.api import deps

router = APIRouter()

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)


@router.post("/", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
async def create_new_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_in: schemas.InvoiceCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create a new invoice with its line items.
    """
    organization = await deps.get_valid_organization_for_user(
        db=db, org_id=invoice_in.organization_id, current_user=current_user
    )

    customer = await crud.customer.get_customer(db, customer_id=invoice_in.customer_id)
    if not customer or customer.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer not found or does not belong to the specified organization."
        )
    
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
    """
    if organization_id:
        await deps.get_valid_organization_for_user(
            db=db, org_id=organization_id, current_user=current_user
        )

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
    
    summaries = []
    for inv in invoices:
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
    invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
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
    invoice_in: schemas.InvoiceUpdate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update an invoice. Ensures the invoice belongs to the current user.
    """
    db_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    await deps.get_valid_organization_for_user(
        db=db, org_id=db_invoice.organization_id, current_user=current_user
    )

    if invoice_in.customer_id and invoice_in.customer_id != db_invoice.customer_id:
        new_customer = await crud.customer.get_customer(db, customer_id=invoice_in.customer_id)
        if not new_customer or new_customer.organization_id != db_invoice.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New customer not found or does not belong to the invoice's organization."
            )
    
    if invoice_in.line_items is not None:
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
    
    await deps.get_valid_organization_for_user(
        db=db, org_id=db_invoice.organization_id, current_user=current_user
    )

    deleted_invoice_data = await crud.invoice.delete_invoice(db=db, db_invoice=db_invoice)
    return deleted_invoice_data

@router.get("/{invoice_id}/pdf", response_class=Response)
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Response:
    """
    Download a specific invoice as a PDF, using the organization's selected
    template or the system default template.
    """
    invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Ensure the organization (which holds the template preference) is valid for the user
    # The get_invoice already loads the organization via joinedload in crud_invoice
    # but this check is for authorization on the organization itself.
    db_organization = await deps.get_valid_organization_for_user(
        db=db, org_id=invoice.organization_id, current_user=current_user
    )

    # --- START: Determine Template Path ---
    template_file_name_to_use: Optional[str] = None

    # The invoice.organization should have selected_invoice_template eagerly loaded
    # due to lazy="selectin" in Organization model and get_invoice in crud.invoice
    # However, let's explicitly refresh if needed or access it safely.
    
    # It's good practice to ensure relationships are loaded if you depend on them.
    # The get_invoice in crud.invoice already does joinedload(InvoiceModel.organization)
    # which *should* bring selected_invoice_template if the relationship is set up for eager loading.
    # If invoice.organization.selected_invoice_template is None after get_invoice, it means no template is selected.

    if invoice.organization and invoice.organization.selected_invoice_template:
        template_file_name_to_use = invoice.organization.selected_invoice_template.template_file_path
        print(f"DEBUG: Using organization's selected template: {template_file_name_to_use}")
    else:
        print(f"DEBUG: Organization (ID: {invoice.organization_id}) has no specific template selected. Looking for system default.")
        system_default_template = await crud.invoice_template.get_system_default_template(db)
        if system_default_template:
            template_file_name_to_use = system_default_template.template_file_path
            print(f"DEBUG: Using system default template: {template_file_name_to_use}")
        else:
            # Fallback if no system default is found (should ideally not happen)
            print(f"WARNING: No system default template found. Falling back to hardcoded 'classic_default_invoice.html'")
            template_file_name_to_use = "classic_default_invoice.html" 
            # Or raise an error:
            # raise HTTPException(status_code=500, detail="Invoice template configuration error: No system default template found.")

    if not template_file_name_to_use:
        # This case should be rare if the fallback logic is robust
        raise HTTPException(status_code=500, detail="Could not determine invoice template to use.")
    # --- END: Determine Template Path ---

    # Ensure other necessary related data is loaded for the template context
    # (get_invoice in crud.invoice should handle most of this)
    if not invoice.customer: await db.refresh(invoice, attribute_names=['customer'])
    # For line_items and their nested item.images, get_invoice in crud.invoice uses selectinload.

    template_context = {"invoice": invoice, "SERVER_HOST": settings.SERVER_HOST}

    try:
        print(f"DEBUG: Attempting to load Jinja template: {template_file_name_to_use}")
        template = jinja_env.get_template(template_file_name_to_use) # Use dynamic template name
        html_content = template.render(template_context)
    except Exception as e:
        print(f"Error rendering template '{template_file_name_to_use}' for invoice PDF: {e}")
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating invoice: Template rendering failed using '{template_file_name_to_use}'.")

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            pdf_bytes = await loop.run_in_executor(
                pool,
                lambda: HTML(string=html_content, base_url=str(TEMPLATE_DIR.parent)).write_pdf() # Use TEMPLATE_DIR.parent as base for relative static assets if any are in templates/
            )
    except Exception as e:
        print(f"Error generating PDF with WeasyPrint for invoice using template '{template_file_name_to_use}': {e}")
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating invoice: PDF conversion failed. Details: {str(e)}")

    filename = f"Invoice-{invoice.invoice_number.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/{invoice_id}/transform-to-commercial", response_model=schemas.Invoice)
async def transform_invoice_to_commercial(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    new_invoice_number: Optional[str] = Query(None, description="Optional new invoice number for the commercial invoice.")
) -> Any:
    """
    Transforms a Pro Forma invoice into a new Commercial invoice.
    """
    pro_forma_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not pro_forma_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pro Forma Invoice not found")
    if pro_forma_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions for this invoice")
    
    await deps.get_valid_organization_for_user(
        db=db, org_id=pro_forma_invoice.organization_id, current_user=current_user
    )
    
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    return commercial_invoice


@router.post("/{commercial_invoice_id}/generate-packing-list", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
async def generate_packing_list_from_invoice(
    commercial_invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    new_packing_list_number: Optional[str] = Query(None, description="Optional new number for the Packing List.")
) -> Any:
    """
    Generates a new Packing List from an existing Commercial Invoice.
    """
    commercial_invoice = await crud.invoice.get_invoice(db, invoice_id=commercial_invoice_id)
    if not commercial_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commercial Invoice not found")
    if commercial_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions for this invoice")

    await deps.get_valid_organization_for_user(
        db=db, org_id=commercial_invoice.organization_id, current_user=current_user
    )

    if commercial_invoice.invoice_type != schemas.InvoiceTypeEnum.COMMERCIAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Commercial invoices can be used to generate a Packing List."
        )

    try:
        packing_list_invoice = await crud.invoice.create_packing_list_from_commercial(
            db=db,
            commercial_invoice=commercial_invoice,
            new_packing_list_number=new_packing_list_number
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return packing_list_invoice

@router.get("/{invoice_id}/packing-list-pdf", response_class=Response)
async def download_packing_list_pdf(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Response:
    """
    Download a Packing List PDF.
    """
    packing_list_data_source = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    
    if not packing_list_data_source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document for Packing List not found")
    if packing_list_data_source.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    await deps.get_valid_organization_for_user(
        db=db, org_id=packing_list_data_source.organization_id, current_user=current_user
    )

    if not packing_list_data_source.organization: await db.refresh(packing_list_data_source, ['organization'])
    if not packing_list_data_source.customer: await db.refresh(packing_list_data_source, ['customer'])
    # Eager loading in crud.invoice.get_invoice should handle line_items and nested item/images

    template_context = {"invoice": packing_list_data_source, "SERVER_HOST": settings.SERVER_HOST}
    
    try:
        template = jinja_env.get_template("packing_list_template.html")
        html_content = template.render(template_context)
    except Exception as e:
        print(f"Error rendering packing list template: {e}")
        raise HTTPException(status_code=500, detail="Error generating packing list: Template rendering failed.")

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            pdf_bytes = await loop.run_in_executor(
                pool,
                lambda: HTML(string=html_content, base_url=settings.SERVER_HOST).write_pdf()
            )
    except Exception as e:
        print(f"Error generating packing list PDF with WeasyPrint: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating packing list: PDF conversion failed.")

    filename = f"PackingList-{packing_list_data_source.invoice_number.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/{invoice_id}/record-payment", response_model=schemas.Invoice)
async def record_invoice_payment(
    invoice_id: uuid.UUID,
    *,
    db: AsyncSession = Depends(get_db),
    payment_details: schemas.PaymentRecordIn,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Record a payment made against a specific invoice.
    """
    db_invoice = await crud.invoice.get_invoice(db, invoice_id=invoice_id)
    if not db_invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if db_invoice.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions for this invoice")

    await deps.get_valid_organization_for_user(
        db=db, org_id=db_invoice.organization_id, current_user=current_user
    )

    if db_invoice.status == schemas.InvoiceStatusEnum.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice is already fully paid.")
    if db_invoice.status == schemas.InvoiceStatusEnum.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot record payment for a cancelled invoice.")

    updated_invoice = await crud.invoice.record_payment_for_invoice(
        db=db, db_invoice=db_invoice, payment_in=payment_details
    )
    return updated_invoice