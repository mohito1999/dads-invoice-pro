# backend/app/services/ai_orchestrator.py
import json
from typing import List, Dict, Any, Optional, Tuple
import uuid
import traceback # For detailed error logging
from datetime import date # For record_payment_func

from google import genai
from google.genai import types

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app import crud, schemas, models # Ensure all necessary schemas are imported
from app.ai_tools.tool_definitions import ALL_TOOLS

# Initialize the Gemini Client
gemini_sdk_client: Optional[genai.Client] = None
if settings.GOOGLE_GEMINI_API_KEY:
    try:
        gemini_sdk_client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
        print("Gemini SDK client initialized successfully with google-genai.")
    except Exception as e:
        print(f"Failed to initialize Gemini SDK client with google-genai: {e}")
        traceback.print_exc()
        gemini_sdk_client = None
else:
    print("WARNING: GOOGLE_GEMINI_API_KEY not found in settings. Gemini client not configured.")

# Helper function to make a Pydantic model's dump JSON-serializable
def make_model_dump_json_serializable(model_data: Dict[str, Any]) -> Dict[str, Any]:
    serializable_data = {}
    for key, value in model_data.items():
        if isinstance(value, uuid.UUID):
            serializable_data[key] = str(value)
        elif isinstance(value, date): # Add date handling
            serializable_data[key] = value.isoformat()
        elif isinstance(value, list):
            processed_list = []
            for item in value:
                if isinstance(item, dict):
                    processed_list.append(make_model_dump_json_serializable(item))
                elif isinstance(item, uuid.UUID):
                    processed_list.append(str(item))
                elif isinstance(item, date):
                    processed_list.append(item.isoformat())
                else:
                    processed_list.append(item)
            serializable_data[key] = processed_list
        elif isinstance(value, dict):
            serializable_data[key] = make_model_dump_json_serializable(value)
        else:
            serializable_data[key] = value
    return serializable_data

# --- Tool Execution Mappers ---
async def execute_get_customer_by_name(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, company_name: str) -> Dict[str, Any]:
    customer = await crud.customer.get_customer_by_company_name_for_org(db, company_name=company_name, organization_id=org_id)
    if customer:
        customer_dict = schemas.Customer.model_validate(customer).model_dump()
        return {"status": "success", "customer_id": str(customer.id), "data": make_model_dump_json_serializable(customer_dict)}
    return {"status": "not_found", "message": f"Customer '{company_name}' not found."}

async def execute_create_customer_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    if "company_name" not in kwargs or not kwargs["company_name"]:
        return {"status": "error", "message": "Company name is required to create a customer."}
    
    customer_data_in = {k: v for k, v in kwargs.items() if v is not None and v != ""} # Filter out None and empty strings
    customer_schema = schemas.CustomerCreate(organization_id=org_id, **customer_data_in)
    
    existing_customer = await crud.customer.get_customer_by_company_name_for_org(
        db, company_name=customer_schema.company_name, organization_id=org_id
    )
    if existing_customer:
        existing_customer_dict = schemas.Customer.model_validate(existing_customer).model_dump()
        return {"status": "already_exists", "customer_id": str(existing_customer.id), "data": make_model_dump_json_serializable(existing_customer_dict)}
    try:
        new_customer = await crud.customer.create_customer(db, customer_in=customer_schema)
        new_customer_dict = schemas.Customer.model_validate(new_customer).model_dump()
        return {"status": "success", "customer_id": str(new_customer.id), "data": make_model_dump_json_serializable(new_customer_dict)}
    except Exception as e: 
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to create customer: {str(e)}"}
    
async def execute_update_customer_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, customer_id: str, **kwargs) -> Dict[str, Any]:
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        return {"status": "error", "message": f"Invalid customer_id format: {customer_id}"}
    db_customer = await crud.customer.get_customer(db, customer_id=customer_uuid)
    if not db_customer:
        return {"status": "not_found", "message": f"Customer with ID '{customer_id}' not found."}
    if db_customer.organization_id != org_id: # Authorization check
        return {"status": "auth_error", "message": "Customer does not belong to the active organization."}
    
    update_data_in = {k: v for k, v in kwargs.items() if v is not None} # Allow empty strings if user wants to clear a field
    customer_update_schema = schemas.CustomerUpdate(**update_data_in)
    try:
        updated_customer = await crud.customer.update_customer(db, db_obj=db_customer, obj_in=customer_update_schema)
        updated_customer_dict = schemas.Customer.model_validate(updated_customer).model_dump()
        return {"status": "success", "customer_id": str(updated_customer.id), "data": make_model_dump_json_serializable(updated_customer_dict)}
    except Exception as e: # Catch potential duplicate name errors from CRUD or other issues
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to update customer: {str(e)}"}

async def execute_get_item_by_name(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, item_name: str) -> Dict[str, Any]:
    item = await crud.item.get_item_by_name_for_org(db, name=item_name, organization_id=org_id)
    if item:
        item_dict = schemas.Item.model_validate(item).model_dump()
        return {"status": "success", "item_id": str(item.id), "data": make_model_dump_json_serializable(item_dict)}
    return {"status": "not_found", "message": f"Item '{item_name}' not found."}

async def execute_create_item_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    if "name" not in kwargs or not kwargs["name"]:
        return {"status": "error", "message": "Item name is required."}
    item_data_in = {k: v for k, v in kwargs.items() if v is not None and v != ""}
    item_schema = schemas.ItemCreate(organization_id=org_id, **item_data_in)
    existing_item = await crud.item.get_item_by_name_for_org(db, name=item_schema.name, organization_id=org_id)
    if existing_item:
        existing_item_dict = schemas.Item.model_validate(existing_item).model_dump()
        return {"status": "already_exists", "item_id": str(existing_item.id), "data": make_model_dump_json_serializable(existing_item_dict)}
    try:
        new_item = await crud.item.create_item(db, item_in=item_schema)
        new_item_dict = schemas.Item.model_validate(new_item).model_dump()
        return {"status": "success", "item_id": str(new_item.id), "data": make_model_dump_json_serializable(new_item_dict)}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to create item: {str(e)}"}

async def execute_get_items_for_organization(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, search_term: Optional[str] = None) -> Dict[str, Any]:
    items = await crud.item.get_items_by_organization(db, organization_id=org_id, search=search_term, limit=20) # Limit for AI context
    if items:
        return {"status": "success", "count": len(items), "items": [make_model_dump_json_serializable(schemas.ItemSummary.model_validate(item).model_dump()) for item in items]}
    return {"status": "not_found", "message": "No items found" + (f" matching '{search_term}'." if search_term else " for this organization.")}

async def execute_get_item_details_by_id(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, item_id: str) -> Dict[str, Any]:
    try:
        item_uuid = uuid.UUID(item_id)
        item = await crud.item.get_item(db, item_id=item_uuid)
        if item and item.organization_id == org_id:
            return {"status": "success", "data": make_model_dump_json_serializable(schemas.Item.model_validate(item).model_dump())}
        elif item: return {"status": "auth_error", "message": "Item does not belong to active organization."}
        return {"status": "not_found", "message": f"Item with ID '{item_id}' not found."}
    except ValueError: return {"status": "error", "message": "Invalid item_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Unexpected error getting item details: {str(e)}"}

async def execute_update_item_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, item_id: str, **kwargs) -> Dict[str, Any]:
    try:
        item_uuid = uuid.UUID(item_id)
        db_item = await crud.item.get_item(db, item_id=item_uuid)
        if not db_item: return {"status": "not_found", "message": f"Item ID '{item_id}' not found."}
        if db_item.organization_id != org_id: return {"status": "auth_error", "message": "Not authorized for this item."}
        
        update_data_in = {k: v for k, v in kwargs.items() if v is not None}
        item_update_schema = schemas.ItemUpdate(**update_data_in)
        updated_item = await crud.item.update_item(db, db_obj=db_item, obj_in=item_update_schema)
        return {"status": "success", "data": make_model_dump_json_serializable(schemas.Item.model_validate(updated_item).model_dump())}
    except ValueError: return {"status": "error", "message": "Invalid item_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Failed to update item: {str(e)}"}

async def execute_delete_item_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, item_id: str) -> Dict[str, Any]:
    try:
        item_uuid = uuid.UUID(item_id)
        db_item = await crud.item.get_item(db, item_id=item_uuid)
        if not db_item: return {"status": "not_found", "message": f"Item ID '{item_id}' not found."}
        if db_item.organization_id != org_id: return {"status": "auth_error", "message": "Not authorized for this item."}
        
        # Note: crud.item.delete_item should handle physical file deletion logic for images if implemented
        await crud.item.delete_item(db, db_obj=db_item)
        return {"status": "success", "message": f"Item '{db_item.name}' (ID: {item_id}) deleted."}
    except ValueError: return {"status": "error", "message": "Invalid item_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Failed to delete item: {str(e)}"}

# --- Invoice Tool Executors ---
async def execute_create_invoice_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **llm_provided_args) -> Dict[str, Any]:
    # ... (Implementation from our previous successful version, ensure it's robust) ...
    try:
        raw_line_items = llm_provided_args.get("line_items", [])
        parsed_line_items = []
        invoice_currency = str(llm_provided_args.get("currency", "USD")).upper()

        for li_data in raw_line_items:
            if "currency" not in li_data or not li_data["currency"]:
                li_data["currency"] = invoice_currency
            price_per_type_val = str(li_data.get("price_per_type", "UNIT")).upper()
            try: li_data["price_per_type"] = schemas.PricePerTypeEnum(price_per_type_val)
            except ValueError: li_data["price_per_type"] = schemas.PricePerTypeEnum.UNIT
            try: li_data["price"] = float(li_data["price"])
            except: return {"status": "error", "message": f"Invalid price for item '{li_data.get('item_description')}'."}
            for qty_field in ["quantity_units", "quantity_cartons", "net_weight_kgs", "gross_weight_kgs", "measurement_cbm"]:
                if qty_field in li_data and li_data[qty_field] is not None and li_data[qty_field] != '':
                    try: li_data[qty_field] = float(li_data[qty_field])
                    except: return {"status": "error", "message": f"Invalid value for {qty_field} on item '{li_data.get('item_description')}'."}
                elif li_data.get(qty_field) == '': li_data[qty_field] = None
            parsed_line_items.append(schemas.InvoiceItemCreate(**li_data))

        invoice_create_args = {
            "organization_id": org_id, "customer_id": uuid.UUID(llm_provided_args["customer_id"]),
            "invoice_number": llm_provided_args.get("invoice_number", f"INV-{uuid.uuid4().hex[:6].upper()}"),
            "invoice_date": llm_provided_args.get("invoice_date"), "due_date": llm_provided_args.get("due_date"),
            "invoice_type": schemas.InvoiceTypeEnum(str(llm_provided_args["invoice_type"]).upper()), "currency": invoice_currency,
            "line_items": parsed_line_items, "comments_notes": llm_provided_args.get("comments_notes"),
            "tax_percentage": float(llm_provided_args["tax_percentage"]) if llm_provided_args.get("tax_percentage") is not None else None,
            "discount_percentage": float(llm_provided_args["discount_percentage"]) if llm_provided_args.get("discount_percentage") is not None else None,
            "container_number": llm_provided_args.get("container_number"), "seal_number": llm_provided_args.get("seal_number"),
            "hs_code": llm_provided_args.get("hs_code"), "bl_number": llm_provided_args.get("bl_number"),
            "status": schemas.InvoiceStatusEnum(str(llm_provided_args.get("status", "DRAFT")).upper())
        }
        invoice_create_schema = schemas.InvoiceCreate(**invoice_create_args)
        new_invoice = await crud.invoice.create_invoice_with_items(db, invoice_in=invoice_create_schema, owner_id=user_id)
        new_invoice_dict = schemas.Invoice.model_validate(new_invoice).model_dump()
        return {"status": "success", "invoice_id": str(new_invoice.id), "data": make_model_dump_json_serializable(new_invoice_dict)}
    except KeyError as e: return {"status": "error", "message": f"Missing required argument for invoice: {str(e)}"}
    except ValueError as e: return {"status": "error", "message": f"Invalid data for invoice: {str(e)}"}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Unexpected error creating invoice: {str(e)}"}

async def execute_get_invoices_for_user(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    # kwargs can include customer_id, status, invoice_number_search, date_from, date_to
    status_enum = schemas.InvoiceStatusEnum(kwargs["status"].upper()) if kwargs.get("status") else None
    customer_uuid = uuid.UUID(kwargs["customer_id"]) if kwargs.get("customer_id") else None
    date_from_obj = date.fromisoformat(kwargs["date_from"]) if kwargs.get("date_from") else None
    date_to_obj = date.fromisoformat(kwargs["date_to"]) if kwargs.get("date_to") else None

    invoices = await crud.invoice.get_invoices_by_user(
        db, user_id=user_id, organization_id=org_id,
        status=status_enum, customer_id=customer_uuid,
        invoice_number_search=kwargs.get("invoice_number_search"),
        date_from=date_from_obj, date_to=date_to_obj,
        limit=20 # Limit for AI context
    )
    if invoices:
        summaries = [make_model_dump_json_serializable(schemas.InvoiceSummary.model_validate(inv).model_dump(context={"customer_repo": crud.customer, "db_session": db})) for inv in invoices] # Hack for customer name, improve later
        return {"status": "success", "count": len(summaries), "invoices": summaries}
    return {"status": "not_found", "message": "No invoices found matching criteria."}


async def execute_get_invoice_details_by_id(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, invoice_id: str) -> Dict[str, Any]:
    try:
        inv_uuid = uuid.UUID(invoice_id)
        invoice = await crud.invoice.get_invoice(db, invoice_id=inv_uuid)
        if invoice and invoice.organization_id == org_id and invoice.user_id == user_id:
            return {"status": "success", "data": make_model_dump_json_serializable(schemas.Invoice.model_validate(invoice).model_dump())}
        elif invoice: return {"status": "auth_error", "message": "Not authorized for this invoice."}
        return {"status": "not_found", "message": f"Invoice ID '{invoice_id}' not found."}
    except ValueError: return {"status": "error", "message": "Invalid invoice_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": str(e)}


async def execute_update_invoice_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, invoice_id: str, **kwargs) -> Dict[str, Any]:
    try:
        inv_uuid = uuid.UUID(invoice_id)
        db_invoice = await crud.invoice.get_invoice(db, invoice_id=inv_uuid)
        if not db_invoice: return {"status": "not_found", "message": f"Invoice ID '{invoice_id}' not found for update."}
        if db_invoice.organization_id != org_id or db_invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized to update this invoice."}

        update_data_in = {k: v for k, v in kwargs.items() if v is not None} # Allow empty strings
        
        # Handle line_items separately if present
        if "line_items" in update_data_in:
            raw_line_items = update_data_in.pop("line_items", [])
            parsed_line_items = []
            invoice_currency = str(update_data_in.get("currency", db_invoice.currency)).upper()
            for li_data in raw_line_items:
                if "currency" not in li_data or not li_data["currency"]: li_data["currency"] = invoice_currency
                price_per_type_val = str(li_data.get("price_per_type", "UNIT")).upper()
                try: li_data["price_per_type"] = schemas.PricePerTypeEnum(price_per_type_val)
                except ValueError: li_data["price_per_type"] = schemas.PricePerTypeEnum.UNIT
                try: li_data["price"] = float(li_data["price"])
                except: return {"status": "error", "message": f"Invalid price for item '{li_data.get('item_description')}' in update."}
                # Handle quantities
                for qty_field in ["quantity_units", "quantity_cartons", "net_weight_kgs", "gross_weight_kgs", "measurement_cbm"]:
                    if qty_field in li_data and li_data[qty_field] is not None and li_data[qty_field] != '':
                        try: li_data[qty_field] = float(li_data[qty_field])
                        except (ValueError, TypeError): return {"status": "error", "message": f"Invalid value for {qty_field} on item '{li_data.get('item_description')}'."}
                    elif li_data.get(qty_field) == '': li_data[qty_field] = None
                parsed_line_items.append(schemas.InvoiceItemCreate(**li_data)) # Use Create schema for new/replacement list
            update_data_in["line_items"] = parsed_line_items

        invoice_update_schema = schemas.InvoiceUpdate(**update_data_in)
        updated_invoice = await crud.invoice.update_invoice_with_items(db, db_invoice=db_invoice, invoice_in=invoice_update_schema)
        return {"status": "success", "data": make_model_dump_json_serializable(schemas.Invoice.model_validate(updated_invoice).model_dump())}
    except ValueError as e: return {"status": "error", "message": f"Invalid data for invoice update: {str(e)}."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Failed to update invoice: {str(e)}"}


async def execute_delete_invoice_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, invoice_id: str) -> Dict[str, Any]:
    try:
        inv_uuid = uuid.UUID(invoice_id)
        db_invoice = await crud.invoice.get_invoice(db, invoice_id=inv_uuid)
        if not db_invoice: return {"status": "not_found", "message": f"Invoice ID '{invoice_id}' not found."}
        if db_invoice.organization_id != org_id or db_invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized for this invoice."}
        
        await crud.invoice.delete_invoice(db, db_invoice=db_invoice)
        return {"status": "success", "message": f"Invoice '{db_invoice.invoice_number}' deleted."}
    except ValueError: return {"status": "error", "message": "Invalid invoice_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": str(e)}

async def execute_signal_download_invoice_pdf(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, invoice_id: str) -> Dict[str, Any]:
    try:
        inv_uuid = uuid.UUID(invoice_id)
        invoice = await crud.invoice.get_invoice(db, invoice_id=inv_uuid) # get_invoice fetches related data
        if not invoice: return {"status": "not_found", "message": f"Invoice ID '{invoice_id}' not found."}
        if invoice.organization_id != org_id or invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized for this invoice."}
        
        doc_type = "invoice"
        if invoice.invoice_type == schemas.InvoiceTypeEnum.PACKING_LIST:
            doc_type = "packing_list"
        
        return {
            "status": "success", 
            "action_type": "DOWNLOAD_DOCUMENT", 
            "document_type": doc_type,
            "invoice_id": invoice_id, 
            "invoice_number": invoice.invoice_number, 
            "message": f"To download the {doc_type.replace('_',' ')} PDF for invoice {invoice.invoice_number}, please use the application's download feature or a dedicated download link."
        }
    except ValueError: return {"status": "error", "message": "Invalid invoice_id format."}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": str(e)}

async def execute_transform_invoice_to_commercial_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, pro_forma_invoice_id: str, new_invoice_number: Optional[str] = None) -> Dict[str, Any]:
    try:
        pf_inv_uuid = uuid.UUID(pro_forma_invoice_id)
        pro_forma_invoice = await crud.invoice.get_invoice(db, invoice_id=pf_inv_uuid)
        if not pro_forma_invoice: return {"status": "not_found", "message": "Pro Forma invoice not found."}
        if pro_forma_invoice.organization_id != org_id or pro_forma_invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized for this Pro Forma invoice."}
        if pro_forma_invoice.invoice_type != schemas.InvoiceTypeEnum.PRO_FORMA:
            return {"status": "error", "message": "Only Pro Forma invoices can be transformed."}
        
        commercial_invoice = await crud.invoice.transform_pro_forma_to_commercial(db, pro_forma_invoice=pro_forma_invoice, new_invoice_number=new_invoice_number)
        return {"status": "success", "data": make_model_dump_json_serializable(schemas.Invoice.model_validate(commercial_invoice).model_dump())}
    except ValueError as e: return {"status": "error", "message": str(e)} # Handles bad UUID or "Only Pro Forma..."
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Transformation failed: {str(e)}"}

async def execute_generate_packing_list_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, commercial_invoice_id: str, new_packing_list_number: Optional[str] = None) -> Dict[str, Any]:
    try:
        comm_inv_uuid = uuid.UUID(commercial_invoice_id)
        commercial_invoice = await crud.invoice.get_invoice(db, invoice_id=comm_inv_uuid)
        if not commercial_invoice: return {"status": "not_found", "message": "Commercial invoice not found."}
        if commercial_invoice.organization_id != org_id or commercial_invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized for this Commercial invoice."}
        if commercial_invoice.invoice_type != schemas.InvoiceTypeEnum.COMMERCIAL:
            return {"status": "error", "message": "Only Commercial invoices can generate Packing Lists."}

        packing_list = await crud.invoice.create_packing_list_from_commercial(db, commercial_invoice=commercial_invoice, new_packing_list_number=new_packing_list_number)
        return {"status": "success", "data": make_model_dump_json_serializable(schemas.Invoice.model_validate(packing_list).model_dump())}
    except ValueError as e: return {"status": "error", "message": str(e)}
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Packing List generation failed: {str(e)}"}

async def execute_record_payment_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, invoice_id: str, amount_paid_now: float, payment_date: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    try:
        inv_uuid = uuid.UUID(invoice_id)
        db_invoice = await crud.invoice.get_invoice(db, invoice_id=inv_uuid)
        if not db_invoice: return {"status": "not_found", "message": f"Invoice ID '{invoice_id}' not found."}
        if db_invoice.organization_id != org_id or db_invoice.user_id != user_id:
            return {"status": "auth_error", "message": "Not authorized for this invoice."}

        payment_date_obj = date.fromisoformat(payment_date) if payment_date else date.today()
        payment_in_schema = schemas.PaymentRecordIn(
            amount_paid_now=amount_paid_now,
            payment_date=payment_date_obj,
            payment_method=kwargs.get("payment_method"),
            notes=kwargs.get("notes")
        )
        updated_invoice = await crud.invoice.record_payment_for_invoice(db, db_invoice=db_invoice, payment_in=payment_in_schema)
        return {"status": "success", "data": make_model_dump_json_serializable(schemas.Invoice.model_validate(updated_invoice).model_dump())}
    except ValueError as e: return {"status": "error", "message": f"Invalid data for payment: {str(e)}."} # Bad UUID or date
    except Exception as e: traceback.print_exc(); return {"status": "error", "message": f"Failed to record payment: {str(e)}"}


TOOL_EXECUTORS = {
    "get_customer_by_name": execute_get_customer_by_name,
    "create_customer_func": execute_create_customer_func,
    "update_customer_func": execute_update_customer_func,
    "get_item_by_name": execute_get_item_by_name,
    "create_item_func": execute_create_item_func,
    "get_items_for_organization": execute_get_items_for_organization,
    "get_item_details_by_id": execute_get_item_details_by_id,
    "update_item_func": execute_update_item_func,
    "delete_item_func": execute_delete_item_func,
    "create_invoice_func": execute_create_invoice_func,
    "get_invoices_for_user": execute_get_invoices_for_user,
    "get_invoice_details_by_id": execute_get_invoice_details_by_id,
    "update_invoice_func": execute_update_invoice_func,
    "delete_invoice_func": execute_delete_invoice_func,
    "signal_download_invoice_pdf": execute_signal_download_invoice_pdf,
    "transform_invoice_to_commercial_func": execute_transform_invoice_to_commercial_func,
    "generate_packing_list_func": execute_generate_packing_list_func,
    "record_payment_func": execute_record_payment_func,
    # "ask_clarifying_question" does not have an executor as it's handled directly
}

# --- Orchestration Logic (process_user_message function) ---
async def process_user_message(
    db: AsyncSession,
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    current_user: models.User,
    active_organization: Optional[models.Organization]
) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    
    if not gemini_sdk_client:
        return "AI service is currently unavailable (client not initialized).", conversation_history, None
    if not active_organization: # This check is important
        return "Please select an active organization first to use AI features.", conversation_history, None

    # Prepare history for google-genai SDK
    gemini_sdk_history: List[types.Content] = []
    for entry in conversation_history:
        role = entry.get("role")
        parts_data_list = entry.get("parts", [])
        if not isinstance(parts_data_list, list): parts_data_list = [parts_data_list]

        gemini_parts_for_content: List[types.Part] = []
        actual_gemini_role_for_history = role 

        for p_item in parts_data_list:
            if role == "user" or role == "model":
                text_content = p_item if isinstance(p_item, str) else p_item.get("text", "")
                if text_content: gemini_parts_for_content.append(types.Part.from_text(text=text_content))
            elif role == "function_call_request": 
                if isinstance(p_item, dict) and "name" in p_item and "args" in p_item:
                    gemini_parts_for_content.append(types.Part.from_function_call(
                        name=p_item["name"], args=p_item["args"]
                    ))
                actual_gemini_role_for_history = "model" 
            elif role == "function_call_response":
                # Omit from initial history for client.chats.create()
                continue 
        
        if gemini_parts_for_content:
            gemini_sdk_history.append(types.Content(role=actual_gemini_role_for_history, parts=gemini_parts_for_content))
        elif role != "function_call_response": 
             print(f"Warning: No parts created for history entry role '{role}', data: {entry}")
    
    # System instruction using the CoT/ReAct style
    system_instruction_text = f"""
    You are "ProVoice AI", a meticulous and intelligent assistant for Dad's Invoice Pro.
    Your primary goal is to understand the user's request, form a plan by thinking step-by-step, execute the plan using available tools, and respond clearly.
    The current user is '{current_user.email}' and the active organization is '{active_organization.name}' (ID: {active_organization.id}). All actions apply to this organization.

    **Core Principle: Contextual Awareness**
    *   **Remember Recent Entities:** If you have just discussed or presented details for a specific entity (e.g., an invoice with ID 'X' and number 'RC-0072', or a customer 'Y'), and the user's next command seems to refer to "that invoice" or "that customer" without re-stating the ID/name, **you MUST try to use the ID of that recently discussed entity** for any subsequent tool calls that require it.
    *   **If Unsure, Clarify with ID:** If the user says "transform the invoice" and you just showed them three invoices, use `ask_clarifying_question` to ask "Which invoice ID would you like to transform?".
    *   **ID Priority:** If a tool requires an ID, always prioritize using a known, valid UUID. If you only have a name/number, your first step should be to use a 'get by name/number' tool to find the ID.

    **Your Thought Process (Follow this strictly for every user request):**
    1.  **Goal:** What is the user trying to achieve? Summarize this internally.
    2.  **Information Check & Contextual Recall:**
        *   Do I have all necessary information for the goal?
        *   Does this request implicitly refer to an entity (invoice, customer, item) from the last 1-2 turns of our conversation? If so, what is its ID?
    3.  **Tool Check & Plan (First Step / Next Step):**
        *   Based on the Goal and current information (including recalled context), what is the single most logical tool to call?
        *   Do I need to check for existing entities *again* if the user's reference is ambiguous (e.g., "the Smith invoice" when there are multiple Smiths)?
    4.  **Clarification (If Needed):** If information is missing (especially a required ID that you can't infer from recent context) or ambiguous for THIS PLANNED TOOL CALL, use the `ask_clarifying_question` tool.
    5.  **Execution & Observation:** (As before)
    6.  **Re-evaluate & Plan Next Step / Respond to User:** (As before)

    **Tool Usage Guidelines:**
    *   **IDs are Critical:** Many tools require specific UUIDs. These UUIDs MUST be obtained from previous successful `get_..._by_name`, `get_..._by_id`, or `create_..._func` calls within the current conversation. Do NOT invent UUIDs. If you need an ID and don't have it, your plan must include a step to get it.
    *   **Existence Checks:** ALWAYS check if a customer or item exists using `get_customer_by_name` or `get_item_by_name` before attempting to create a new one for that *same name*, unless the user explicitly says "create a NEW customer/item". If it exists, use its ID.
    **Transforming/Generating from Existing:**
        *   When using `transform_invoice_to_commercial_func` or `generate_packing_list_func`, the user might say "transform the pro forma invoice we just talked about" or "generate a packing list for that commercial invoice". You MUST use the ID of the invoice that was the subject of the recent conversation for the `pro_forma_invoice_id` or `commercial_invoice_id` parameter. If you are not certain which ID to use, ask for clarification using the invoice number or ID.
    *   **Optional Fields:** If the user doesn't provide optional information for creation/updates, that's okay; the tools will handle them as null/default. Only ask for optional fields if they are crucial for the user's stated goal or if a tool fails due to their absence for a specific operation.
    *   **Invoice Line Items (Iterative Process for `create_invoice_func` or `update_invoice_func`):**
        *   Confirm the customer ID first.
        *   Ask for invoice header details (type, currency).
        *   Then, for EACH item: ask for description, quantity, price. Check/create item master if needed (`get_item_by_name`, then `create_item_func`). Collect all line item details.
        *   After all items, ask for final details (notes, tax, etc.).
        *   Then, call `create_invoice_func` or `update_invoice_func` with the complete payload.
    *   **PDFs:** The `signal_download_invoice_pdf` tool tells the system the user wants a PDF. Your response should just be an acknowledgement like, "Okay, you can download the PDF for invoice [number] now." The system handles the actual download mechanism.

    Be helpful, clear, and ensure you have necessary information before acting. Break down complex requests.
    """
    
    try:
        chat_session = gemini_sdk_client.aio.chats.create( 
            model=f"models/{settings.GEMINI_MODEL_NAME}", 
            history=gemini_sdk_history
        )
                                                     
        print(f"Sending to Gemini. SDK History for create: {len(gemini_sdk_history)}. User message: {user_message}")
        
        current_generation_config = types.GenerateContentConfig(
            tools=ALL_TOOLS,
            # System instruction is now part of the model config or first turn history usually
            # Forcing it on every turn with GenerateContentConfig if history is empty
            system_instruction=system_instruction_text if not gemini_sdk_history else None, 
            temperature=0.5, # Slightly lower temperature for more deterministic planning
        )
        
        response = await chat_session.send_message(
            user_message, 
            config=current_generation_config
        )
    except Exception as e:
        print(f"Error during Gemini chat session creation or initial send_message: {e}")
        traceback.print_exc()
        return "Sorry, I encountered an error trying to process your request with the AI service.", conversation_history, None
    
    ai_response_text = ""
    follow_up_question_for_user = None
    updated_history = list(conversation_history) 
    updated_history.append({"role": "user", "parts": [user_message]})

    current_response = response
    MAX_TOOL_ITERATIONS = 7 # Increased slightly for more complex plans
    tool_iterations = 0

    while tool_iterations < MAX_TOOL_ITERATIONS:
        tool_iterations += 1

        if not current_response or not current_response.function_calls:
            try:
                ai_response_text = current_response.text
                if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                    updated_history.append({"role": "model", "parts": [ai_response_text]})
            except ValueError: 
                # ... (same error handling for .text access as before)
                if current_response and current_response.candidates and current_response.candidates[0].finish_reason:
                    print(f"Candidate Finish Reason: {current_response.candidates[0].finish_reason.name}")
                    if current_response.candidates[0].finish_reason == types.Candidate.FinishReason.SAFETY:
                        ai_response_text = "My response was blocked due to safety settings."
                    else:
                        ai_response_text = f"Response generation stopped: {current_response.candidates[0].finish_reason.name}."
                else:
                    ai_response_text = "I received an empty or complex response from the AI."
                print(f"Response that caused text error or was empty: {current_response}")
                if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                    updated_history.append({"role": "model", "parts": [ai_response_text]})
            except AttributeError: # If current_response is None
                ai_response_text = "An unexpected issue occurred after a tool call. Please try again."
                print(f"current_response was None or missing attributes before accessing .text")
                if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                    updated_history.append({"role": "model", "parts": [ai_response_text]})
            break 

        # Process the first function call if multiple are returned (usually one per turn from Gemini function calling)
        fc_to_process = current_response.function_calls[0]
        tool_name = fc_to_process.name
        tool_args = dict(fc_to_process.args) 

        print(f"LLM wants to call tool: {tool_name} with args: {tool_args}")
        fc_requests_for_history = [{"name": fc.name, "args": dict(fc.args)} for fc in current_response.function_calls]
        if not any(h_entry.get("role") == "function_call_request" and h_entry.get("parts") == fc_requests_for_history for h_entry in updated_history[-2:]):
            updated_history.append({"role": "function_call_request", "parts": fc_requests_for_history})

        if tool_name == "ask_clarifying_question":
            follow_up_question_for_user = tool_args.get("question_to_user", "I need more information. Can you clarify?")
            ai_response_text = follow_up_question_for_user
            if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                updated_history.append({"role": "model", "parts": [ai_response_text]})
            return ai_response_text, updated_history, follow_up_question_for_user

        elif tool_name in TOOL_EXECUTORS:
            executor = TOOL_EXECUTORS[tool_name]
            try:
                tool_result = await executor(db=db, org_id=active_organization.id, user_id=current_user.id, **tool_args)
            except Exception as exec_e:
                print(f"Error executing tool {tool_name}: {exec_e}")
                traceback.print_exc()
                tool_result = {"status": "error", "message": f"System error executing tool {tool_name}: {str(exec_e)}"}
            
            print(f"Tool {tool_name} result: {tool_result}")

            if not any(h_entry.get("role") == "function_call_response" and h_entry.get("parts") == [{"name": tool_name, "response": tool_result}] for h_entry in updated_history[-2:]):
                updated_history.append({"role": "function_call_response", "parts": [{"name": tool_name, "response": tool_result}]})
            
            function_response_part = types.Part.from_function_response(name=tool_name, response=tool_result)
            
            print(f"Sending tool result back to Gemini for {tool_name}")
            try:
                current_response = await chat_session.send_message(function_response_part, config=current_generation_config)
            except Exception as send_e:
                print(f"Error sending tool response to Gemini: {send_e}")
                traceback.print_exc()
                ai_response_text = "Sorry, I encountered an error after processing the tool result."
                if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                     updated_history.append({"role": "model", "parts": [ai_response_text]})
                return ai_response_text, updated_history, None 
        else: 
            ai_response_text = f"Error: System error - Unknown tool '{tool_name}' requested by AI."
            if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                updated_history.append({"role": "model", "parts": [ai_response_text]})
            return ai_response_text, updated_history, None
        
    if tool_iterations >= MAX_TOOL_ITERATIONS and not ai_response_text:
        print("Warning: Reached max tool iterations without a final text response.")
        ai_response_text = "I got into a bit of a processing loop. Could you please simplify your request or try again?"
        if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
            updated_history.append({"role": "model", "parts": [ai_response_text]})

    return ai_response_text, updated_history, follow_up_question_for_user