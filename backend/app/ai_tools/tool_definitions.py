# backend/app/ai_tools/tool_definitions.py
from google.genai import types # Use the new SDK's types module
from typing import List


# --- Tool: Get Customer by Name ---
get_customer_by_name_func = types.FunctionDeclaration(
    name="get_customer_by_name",
    description="Retrieves an existing customer's details from the system by their company name. Use this to check if a customer already exists before creating a new one.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "company_name": types.Schema(type='STRING', description="The exact company name of the customer to search for.")
        },
        required=["company_name"]
    )
)

# --- Tool: Create Customer ---
create_customer_func = types.FunctionDeclaration(
    name="create_customer_func",
    description="Creates a new customer in the system. Only use this if get_customer_by_name confirms the customer does not exist or if explicitly asked to create a new one.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "company_name": types.Schema(type='STRING', description="The company name for the new customer. This is mandatory."),
            "poc_name": types.Schema(type='STRING', description="Point of Contact name for the customer. Optional."),
            "billing_address_line1": types.Schema(type='STRING', description="Billing address line 1. Optional."),
            "billing_address_line2": types.Schema(type='STRING', description="Billing address line 2. Optional."),
            "billing_city": types.Schema(type='STRING', description="Billing city. Optional."),
            "billing_state_province_region": types.Schema(type='STRING', description="Billing state, province, or region. Optional."),
            "billing_zip_code": types.Schema(type='STRING', description="Billing zip or postal code. Optional."),
            "billing_country": types.Schema(type='STRING', description="Billing country. Optional."),
            "email": types.Schema(type='STRING', description="Contact email for the customer. Optional, must be a valid email format."),
            "phone_number": types.Schema(type='STRING', description="Contact phone number for the customer. Optional.")
        },
        required=["company_name"]
    )
)

update_customer_func = types.FunctionDeclaration(
    name="update_customer_func",
    description="Updates an existing customer's details in the system. You MUST provide the customer_id of the customer to update. Use get_customer_by_name first if you only have the name. Only include fields that need to be changed.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "customer_id": types.Schema(type='STRING', description="The UUID of the customer to update. This is mandatory."),
            "company_name": types.Schema(type='STRING', description="The new company name for the customer. Optional."),
            "poc_name": types.Schema(type='STRING', description="New Point of Contact name. Optional."),
            "billing_address_line1": types.Schema(type='STRING', description="New billing address line 1. Optional."),
            "billing_address_line2": types.Schema(type='STRING', description="New billing address line 2. Optional."),
            "billing_city": types.Schema(type='STRING', description="New billing city. Optional."),
            "billing_state_province_region": types.Schema(type='STRING', description="New billing state, province, or region. Optional."),
            "billing_zip_code": types.Schema(type='STRING', description="New billing zip or postal code. Optional."),
            "billing_country": types.Schema(type='STRING', description="New billing country. Optional."),
            "email": types.Schema(type='STRING', description="New contact email for the customer. Optional, must be a valid email format."),
            "phone_number": types.Schema(type='STRING', description="New contact phone number for the customer. Optional.")
        },
        required=["customer_id"] # Only customer_id is strictly required to identify *which* customer to update
    )
)

get_customers_for_organization_func = types.FunctionDeclaration(
    name="get_customers_for_organization",
    description="Lists all customers associated with the current active organization. Can be used to see a list of existing customers or to find a customer if the user is unsure of the exact name.",
    parameters=types.Schema( # This tool currently takes no specific parameters from the LLM, org_id is implicit
        type='OBJECT',
        properties={}, # No specific parameters needed from LLM beyond implicit org context
        required=[]
    )
)

delete_customer_func = types.FunctionDeclaration(
    name="delete_customer_func",
    description="Deletes an existing customer from the system using their unique customer ID. This action is permanent and will also delete associated invoices. The customer_id MUST be provided.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "customer_id": types.Schema(type='STRING', description="The unique UUID of the customer to delete. This must be a valid ID obtained from a previous step.")
        },
        required=["customer_id"]
    )
)


# --- Tool: Get Item by Name ---
get_item_by_name_func = types.FunctionDeclaration(
    name="get_item_by_name",
    description="Retrieves an existing item's details by its name. Useful for checking if an item exists before creating it or adding it to an invoice.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "item_name": types.Schema(type='STRING', description="The name of the item to search for.")
        },
        required=["item_name"]
    )
)

# --- Tool: Create Item ---
create_item_func = types.FunctionDeclaration(
    name="create_item_func",
    description="Creates a new item in the system. Use after confirming the item doesn't exist.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "name": types.Schema(type='STRING', description="The name of the new item. Mandatory."),
            "description": types.Schema(type='STRING', description="A description for the item. Optional."),
            "default_price": types.Schema(type='NUMBER', description="The default price of the item. Must be non-negative. Optional."),
            "default_unit": types.Schema(type='STRING', description="The default unit for the item (e.g., 'piece', 'kg', 'box'). Optional.")
        },
        required=["name"]
    )
)

get_items_for_organization_func = types.FunctionDeclaration(
    name="get_items_for_organization",
    description="Lists all items for the current active organization. Can be used to see available items before adding to an invoice or if the user asks to see their items. Supports optional search by item name.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "search_term": types.Schema(type='STRING', description="Optional: A term to search for within item names.")
        },
        required=[]
    )
)

get_item_details_by_id_func = types.FunctionDeclaration(
    name="get_item_details_by_id",
    description="Retrieves detailed information for a specific item using its unique item ID. Use this if you have an item_id (e.g., from a previous search or creation) and need its full details, including description, price, unit, and any associated image information.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "item_id": types.Schema(type='STRING', description="The unique UUID of the item to retrieve.")
        },
        required=["item_id"]
    )
)

get_item_details_func = types.FunctionDeclaration( # Already had get_item_by_name, this is if by ID
    name="get_item_details_by_id",
    description="Retrieves detailed information for a specific item using its unique ID. Use this if you have an item_id and need full details.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "item_id": types.Schema(type='STRING', description="The UUID of the item to retrieve.")
        },
        required=["item_id"]
    )
)

update_item_func = types.FunctionDeclaration(
    name="update_item_func",
    description="Updates an existing item's details. You MUST provide the item_id. Only include fields that need to be changed. Images are handled separately.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "item_id": types.Schema(type='STRING', description="The UUID of the item to update. Mandatory."),
            "name": types.Schema(type='STRING', description="The new name for the item. Optional."),
            "description": types.Schema(type='STRING', description="New description. Optional."),
            "default_price": types.Schema(type='NUMBER', description="New default price. Optional."),
            "default_unit": types.Schema(type='STRING', description="New default unit. Optional.")
        },
        required=["item_id"]
    )
)

delete_item_func = types.FunctionDeclaration(
    name="delete_item_func",
    description="Deletes an existing item from the system using its unique ID. This action is permanent.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "item_id": types.Schema(type='STRING', description="The UUID of the item to delete.")
        },
        required=["item_id"]
    )
)


# --- Tool: Create Invoice ---
create_invoice_func = types.FunctionDeclaration(
    name="create_invoice_func",
    description="Creates a new invoice (Pro Forma, Commercial, or Packing List) for a specified customer with given line items. Ensure customer and items exist or are created first.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "customer_id": types.Schema(type='STRING', description="The UUID of the customer for whom the invoice is being created. This MUST be obtained by first using get_customer_by_name or create_customer_func."),
            "invoice_number": types.Schema(type='STRING', description="The unique invoice number. If not provided, one might be suggested or auto-generated based on system policy, but it's good to ask the user or suggest one."),
            "invoice_date": types.Schema(type='STRING', description="The date of the invoice in YYYY-MM-DD format. Defaults to today if not provided."),
            "due_date": types.Schema(type='STRING', description="The due date for payment in YYYY-MM-DD format. Optional."),
            "invoice_type": types.Schema(type='STRING', description="The type of invoice. Must be one of: PRO_FORMA, COMMERCIAL, PACKING_LIST."),
            "currency": types.Schema(type='STRING', description="The 3-letter ISO currency code for the invoice (e.g., USD, EUR). Mandatory."),
            "line_items": types.Schema(
                type='ARRAY',
                description="A list of items to include in the invoice. Each item should have description, quantity, price, etc.",
                items=types.Schema(
                    type='OBJECT',
                    properties={
                        "item_id": types.Schema(type='STRING', description="Optional UUID of a pre-existing item. If provided, description, price, unit may be auto-filled but can be overridden."),
                        "item_description": types.Schema(type='STRING', description="Description of the line item. Mandatory."),
                        "quantity_units": types.Schema(type='NUMBER', description="Quantity in units. Optional if quantity_cartons is provided."),
                        "quantity_cartons": types.Schema(type='NUMBER', description="Quantity in cartons. Optional if quantity_units is provided."),
                        "unit_type": types.Schema(type='STRING', description="Unit of measure (e.g., pieces, kg). Defaults to 'pieces' if not provided."),
                        "price": types.Schema(type='NUMBER', description="Price per unit or per carton, depending on price_per_type. Mandatory."),
                        "price_per_type": types.Schema(type='STRING', description="Indicates if the price is per 'UNIT' or per 'CARTON'. Defaults to 'UNIT'."),
                        "net_weight_kgs": types.Schema(type='NUMBER', description="Net weight in kilograms. Optional."),
                        "gross_weight_kgs": types.Schema(type='NUMBER', description="Gross weight in kilograms. Optional."),
                        "measurement_cbm": types.Schema(type='NUMBER', description="Measurement in cubic meters (CBM). Optional."),
                        "item_specific_comments": types.Schema(type='STRING', description="Any specific comments for this line item. Optional."),
                    },
                    required=["item_description", "price"]
                )
            ),
            "comments_notes": types.Schema(type='STRING', description="General comments or notes for the invoice (e.g., payment terms). Optional."),
            "tax_percentage": types.Schema(type='NUMBER', description="Tax percentage to apply to the subtotal (e.g., 10 for 10%). Optional."),
            "discount_percentage": types.Schema(type='NUMBER', description="Discount percentage to apply to the subtotal (e.g., 5 for 5%). Optional."),
            "container_number": types.Schema(type='STRING', description="Container number, if applicable. Optional."),
            "seal_number": types.Schema(type='STRING', description="Seal number, if applicable. Optional."),
            "hs_code": types.Schema(type='STRING', description="Harmonized System (HS) code, if applicable. Optional."),
            "bl_number": types.Schema(type='STRING', description="Bill of Lading (B/L) number, if applicable. Optional."),
            "status": types.Schema(type='STRING', description="The status of the invoice, e.g., DRAFT, UNPAID. Defaults to DRAFT if not specified.")
        },
        required=["customer_id", "invoice_type", "currency", "line_items"]
    )
)

get_invoices_for_user_func = types.FunctionDeclaration(
    name="get_invoices_for_user",
    description="Lists invoices for the current user and active organization. Supports filtering by status, customer, date range, and invoice number search.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "customer_id": types.Schema(type='STRING', description="Optional: UUID of a customer to filter invoices for."),
            "status": types.Schema(type='STRING', description="Optional: Filter by invoice status (e.g., DRAFT, UNPAID, PAID, PARTIALLY_PAID, OVERDUE, CANCELLED)."),
            "invoice_number_search": types.Schema(type='STRING', description="Optional: Search term for invoice numbers."),
            "date_from": types.Schema(type='STRING', description="Optional: Start date (YYYY-MM-DD) to filter invoices from."),
            "date_to": types.Schema(type='STRING', description="Optional: End date (YYYY-MM-DD) to filter invoices to.")
        },
        required=[]
    )
)

get_invoice_details_by_id_func = types.FunctionDeclaration(
    name="get_invoice_details_by_id",
    description="Retrieves all details for a specific invoice using its unique ID.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "invoice_id": types.Schema(type='STRING', description="The UUID of the invoice to retrieve.")
        },
        required=["invoice_id"]
    )
)

update_invoice_func = types.FunctionDeclaration(
    name="update_invoice_func",
    description="Updates an existing invoice. You MUST provide the invoice_id. Only include fields that need to be changed. Line items can be fully replaced if provided.",
    parameters=types.Schema( # This is a simplified version, a full update is complex for LLM to construct
        type='OBJECT',
        properties={
            "invoice_id": types.Schema(type='STRING', description="The UUID of the invoice to update. Mandatory."),
            "invoice_number": types.Schema(type='STRING', description="Optional: New invoice number."),
            "invoice_date": types.Schema(type='STRING', description="Optional: New invoice date (YYYY-MM-DD)."),
            "due_date": types.Schema(type='STRING', description="Optional: New due date (YYYY-MM-DD)."),
            "customer_id": types.Schema(type='STRING', description="Optional: New customer UUID for the invoice."),
            "status": types.Schema(type='STRING', description="Optional: New status (e.g., DRAFT, UNPAID, PAID)."),
            "comments_notes": types.Schema(type='STRING', description="Optional: New comments or notes."),
            # Add other updatable header fields like tax_percentage, discount_percentage, shipping fields
            # Line items update is complex: either replace all or have add/remove/update line item tools.
            # For now, let's assume LLM could provide a new list of line_items to replace existing.
            "line_items": types.Schema(
                type='ARRAY',
                description="Optional: A new list of line items to completely replace the existing ones. Each item requires description, quantity, price.",
                items=types.Schema(type='OBJECT', properties={ # Same as create_invoice_func line_items
                    "item_id": types.Schema(type='STRING', description="Optional UUID..."),
                    "item_description": types.Schema(type='STRING', description="Description... Mandatory."),
                    "quantity_units": types.Schema(type='NUMBER', description="Quantity in units..."),
                    "price": types.Schema(type='NUMBER', description="Price... Mandatory."),
                    # ... other line item fields
                })
            )
        },
        required=["invoice_id"]
    )
)

delete_invoice_func = types.FunctionDeclaration(
    name="delete_invoice_func",
    description="Deletes an existing invoice from the system using its unique ID. This action is permanent.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "invoice_id": types.Schema(type='STRING', description="The UUID of the invoice to delete.")
        },
        required=["invoice_id"]
    )
)

# For PDF download, the AI signals the intent, frontend handles the actual download.
signal_download_invoice_pdf_func = types.FunctionDeclaration(
    name="signal_download_invoice_pdf",
    description="Signals that the user wants to download the PDF for a specific invoice. The system will then provide a way for the user to download it.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "invoice_id": types.Schema(type='STRING', description="The UUID of the invoice whose PDF is to be downloaded.")
        },
        required=["invoice_id"]
    )
)

transform_invoice_to_commercial_func = types.FunctionDeclaration(
    name="transform_invoice_to_commercial_func",
    description="Transforms an existing Pro Forma invoice into a new Commercial invoice. You need the Pro Forma invoice ID.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "pro_forma_invoice_id": types.Schema(type='STRING', description="The UUID of the Pro Forma invoice to transform."),
            "new_invoice_number": types.Schema(type='STRING', description="Optional: A specific invoice number for the new Commercial invoice.")
        },
        required=["pro_forma_invoice_id"]
    )
)

generate_packing_list_func = types.FunctionDeclaration(
    name="generate_packing_list_func",
    description="Generates a new Packing List from an existing Commercial invoice. You need the Commercial invoice ID.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "commercial_invoice_id": types.Schema(type='STRING', description="The UUID of the Commercial invoice to use as a base."),
            "new_packing_list_number": types.Schema(type='STRING', description="Optional: A specific number for the new Packing List.")
        },
        required=["commercial_invoice_id"]
    )
)

record_payment_func = types.FunctionDeclaration(
    name="record_payment_func",
    description="Records a payment made against a specific invoice. Requires invoice ID, amount paid, and payment date.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "invoice_id": types.Schema(type='STRING', description="The UUID of the invoice to record payment for."),
            "amount_paid_now": types.Schema(type='NUMBER', description="The amount being paid in this transaction."),
            "payment_date": types.Schema(type='STRING', description="Date payment was received (YYYY-MM-DD). Defaults to today if not specified."),
            "payment_method": types.Schema(type='STRING', description="Optional: Method of payment (e.g., Bank Transfer, Cash)."),
            "notes": types.Schema(type='STRING', description="Optional: Notes for this payment transaction.")
        },
        required=["invoice_id", "amount_paid_now"]
    )
)


# --- Tool: Ask Clarifying Question ---
ask_clarifying_question_func = types.FunctionDeclaration(
    name="ask_clarifying_question",
    description="Use this function when you need more information from the user to proceed with their request or to clarify ambiguity. The user's response will be provided back to you.",
    parameters=types.Schema(
        type='OBJECT',
        properties={
            "question_to_user": types.Schema(type='STRING', description="The clear and specific question to ask the user.")
        },
        required=["question_to_user"]
    )
)


# Combine all function declarations into a Tool
dad_invoice_pro_tool = types.Tool(
    function_declarations=[
        get_customer_by_name_func,
        create_customer_func,
        update_customer_func,
        get_customers_for_organization_func, # New
        delete_customer_func,                # New
        get_item_by_name_func,      # We had this
        get_items_for_organization_func,
        get_item_details_by_id_func, # New
        create_item_func,           # We had this
        update_item_func,           # New
        delete_item_func,           # New
        create_invoice_func,        # We had this
        get_invoices_for_user_func, # New
        get_invoice_details_by_id_func, # New
        update_invoice_func,        # New
        delete_invoice_func,        # New
        signal_download_invoice_pdf_func, # New
        transform_invoice_to_commercial_func, # New
        generate_packing_list_func, # New
        record_payment_func,        # New
        ask_clarifying_question_func 
    ]
)

# List of all tools to be passed to the Gemini model
ALL_TOOLS: List[types.Tool] = [dad_invoice_pro_tool]