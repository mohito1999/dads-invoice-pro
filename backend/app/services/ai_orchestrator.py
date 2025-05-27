# backend/app/services/ai_orchestrator.py
import json
from typing import List, Dict, Any, Optional, Tuple
import uuid # Ensure uuid is imported
import traceback # For error logging

from google import genai
from google.genai import types

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app import crud, schemas, models
from app.ai_tools.tool_definitions import ALL_TOOLS

# Initialize the Gemini Client
gemini_sdk_client: Optional[genai.Client] = None # Store the main synchronous client
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

# Helper function to make a Pydantic model's dump JSON-serializable (especially for UUIDs)
def make_model_dump_json_serializable(model_data: Dict[str, Any]) -> Dict[str, Any]:
    serializable_data = {}
    for key, value in model_data.items():
        if isinstance(value, uuid.UUID):
            serializable_data[key] = str(value)
        elif isinstance(value, list): # Handle lists of items (e.g., in Invoice data)
            processed_list = []
            for item in value:
                if isinstance(item, dict):
                    processed_list.append(make_model_dump_json_serializable(item))
                elif isinstance(item, uuid.UUID): # handle list of UUIDs if any
                    processed_list.append(str(item))
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
    # user_id is accepted for consistency
    customer = await crud.customer.get_customer_by_company_name_for_org(db, company_name=company_name, organization_id=org_id)
    if customer:
        customer_dict = schemas.Customer.model_validate(customer).model_dump()
        return {"status": "success", "customer_id": str(customer.id), "data": make_model_dump_json_serializable(customer_dict)}
    return {"status": "not_found", "message": f"Customer '{company_name}' not found."}

async def execute_create_customer_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    if "company_name" not in kwargs or not kwargs["company_name"]:
        return {"status": "error", "message": "Company name is required to create a customer."}
    
    customer_data_in = {k: v for k, v in kwargs.items() if v is not None} # Filter out None values for Pydantic create
    customer_data = schemas.CustomerCreate(organization_id=org_id, **customer_data_in)
    
    existing_customer = await crud.customer.get_customer_by_company_name_for_org(
        db, company_name=customer_data.company_name, organization_id=org_id
    )
    if existing_customer:
        existing_customer_dict = schemas.Customer.model_validate(existing_customer).model_dump()
        return {"status": "already_exists", "customer_id": str(existing_customer.id), "data": make_model_dump_json_serializable(existing_customer_dict)}

    try:
        new_customer = await crud.customer.create_customer(db, customer_in=customer_data)
        new_customer_dict = schemas.Customer.model_validate(new_customer).model_dump()
        return {"status": "success", "customer_id": str(new_customer.id), "data": make_model_dump_json_serializable(new_customer_dict)}
    except Exception as e: 
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to create customer: {str(e)}"}
    
async def execute_update_customer_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, customer_id: str, **kwargs) -> Dict[str, Any]:
    """
    Executes the update_customer tool.
    org_id and user_id are for authorization checks.
    customer_id is the ID of the customer to update.
    kwargs contains the fields to update.
    """
    try:
        customer_uuid = uuid.UUID(customer_id) # Convert string ID from LLM to UUID
    except ValueError:
        return {"status": "error", "message": f"Invalid customer_id format: {customer_id}"}

    db_customer = await crud.customer.get_customer(db, customer_id=customer_uuid)
    if not db_customer:
        return {"status": "not_found", "message": f"Customer with ID '{customer_id}' not found."}

    # Authorization check: Does this customer belong to the active organization?
    if db_customer.organization_id != org_id:
        return {"status": "auth_error", "message": "Customer does not belong to the active organization."}

    # Prepare the update schema, only passing fields provided by LLM in kwargs
    customer_update_data = schemas.CustomerUpdate(**kwargs)
    
    try:
        updated_customer = await crud.customer.update_customer(db, db_obj=db_customer, obj_in=customer_update_data)
        updated_customer_dict = schemas.Customer.model_validate(updated_customer).model_dump()
        return {"status": "success", "customer_id": str(updated_customer.id), "data": make_model_dump_json_serializable(updated_customer_dict)}
    except HTTPException as http_exc: # Catch potential duplicate name errors from CRUD/API layer if they raise HTTPException
        return {"status": "error", "message": http_exc.detail}
    except Exception as e:
        return {"status": "error", "message": f"Failed to update customer: {str(e)}"}

async def execute_get_item_by_name(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, item_name: str) -> Dict[str, Any]:
    # user_id is accepted for consistency
    item = await crud.item.get_item_by_name_for_org(db, name=item_name, organization_id=org_id)
    if item:
        item_dict = schemas.Item.model_validate(item).model_dump()
        return {"status": "success", "item_id": str(item.id), "data": make_model_dump_json_serializable(item_dict)}
    return {"status": "not_found", "message": f"Item '{item_name}' not found."}

async def execute_create_item_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    # user_id is accepted for consistency
    if "name" not in kwargs or not kwargs["name"]:
        return {"status": "error", "message": "Item name is required."}
    
    item_data_in = {k: v for k, v in kwargs.items() if v is not None}
    item_data = schemas.ItemCreate(organization_id=org_id, **item_data_in)
    existing_item = await crud.item.get_item_by_name_for_org(db, name=item_data.name, organization_id=org_id)
    if existing_item:
        existing_item_dict = schemas.Item.model_validate(existing_item).model_dump()
        return {"status": "already_exists", "item_id": str(existing_item.id), "data": make_model_dump_json_serializable(existing_item_dict)}
    
    try:
        new_item = await crud.item.create_item(db, item_in=item_data)
        new_item_dict = schemas.Item.model_validate(new_item).model_dump()
        return {"status": "success", "item_id": str(new_item.id), "data": make_model_dump_json_serializable(new_item_dict)}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to create item: {str(e)}"}

async def execute_create_invoice_func(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **llm_provided_args) -> Dict[str, Any]:
    try:
        print(f"DEBUG: execute_create_invoice_func received llm_provided_args: {llm_provided_args}")

        # Validate and parse line items first
        raw_line_items = llm_provided_args.get("line_items", [])
        parsed_line_items = []
        invoice_currency = str(llm_provided_args.get("currency", "USD")).upper() # Get currency early

        for li_data in raw_line_items:
            # Ensure line item currency matches invoice currency if not provided in line item
            if "currency" not in li_data or not li_data["currency"]:
                li_data["currency"] = invoice_currency
            
            price_per_type_val = str(li_data.get("price_per_type", "UNIT")).upper()
            try:
                li_data["price_per_type"] = schemas.PricePerTypeEnum(price_per_type_val)
            except ValueError:
                li_data["price_per_type"] = schemas.PricePerTypeEnum.UNIT 
                print(f"Warning: Invalid price_per_type '{price_per_type_val}' for item '{li_data.get('item_description')}', defaulted to UNIT.")
            
            # Ensure price is a float
            try:
                li_data["price"] = float(li_data["price"])
            except (ValueError, TypeError):
                return {"status": "error", "message": f"Invalid price for item '{li_data.get('item_description')}': must be a number."}

            # Ensure quantities are numbers if provided
            for qty_field in ["quantity_units", "quantity_cartons", "net_weight_kgs", "gross_weight_kgs", "measurement_cbm"]:
                if qty_field in li_data and li_data[qty_field] is not None and li_data[qty_field] != '':
                    try:
                        li_data[qty_field] = float(li_data[qty_field])
                    except (ValueError, TypeError):
                         return {"status": "error", "message": f"Invalid value for {qty_field} on item '{li_data.get('item_description')}': must be a number."}
                elif li_data.get(qty_field) == '': # Convert empty strings to None for optional number fields
                    li_data[qty_field] = None


            parsed_line_items.append(schemas.InvoiceItemCreate(**li_data))

        # Construct arguments for InvoiceCreate explicitly
        invoice_create_args = {
            "organization_id": org_id, # From orchestrator
            "customer_id": uuid.UUID(llm_provided_args["customer_id"]), # From LLM
            "invoice_number": llm_provided_args.get("invoice_number", f"INV-{uuid.uuid4().hex[:6].upper()}"),
            "invoice_date": llm_provided_args.get("invoice_date"), # Pydantic will parse date string
            "due_date": llm_provided_args.get("due_date"),
            "invoice_type": schemas.InvoiceTypeEnum(str(llm_provided_args["invoice_type"]).upper()),
            "currency": invoice_currency,
            "line_items": parsed_line_items,
            "comments_notes": llm_provided_args.get("comments_notes"),
            "tax_percentage": float(llm_provided_args["tax_percentage"]) if llm_provided_args.get("tax_percentage") is not None else None,
            "discount_percentage": float(llm_provided_args["discount_percentage"]) if llm_provided_args.get("discount_percentage") is not None else None,
            "container_number": llm_provided_args.get("container_number"),
            "seal_number": llm_provided_args.get("seal_number"),
            "hs_code": llm_provided_args.get("hs_code"),
            "bl_number": llm_provided_args.get("bl_number"),
            "status": schemas.InvoiceStatusEnum(str(llm_provided_args.get("status", "DRAFT")).upper())
        }
        
        # Filter out None values for optional fields to avoid passing them if not intended
        # Pydantic models handle optional fields defaulting to None if not provided, so this isn't strictly necessary
        # if the schema defines them as Optional. But it's cleaner if LLM omits them.
        # final_invoice_create_args = {k: v for k, v in invoice_create_args.items() if v is not None}

        invoice_create_schema = schemas.InvoiceCreate(**invoice_create_args)
        
        new_invoice = await crud.invoice.create_invoice_with_items(db, invoice_in=invoice_create_schema, owner_id=user_id)
        new_invoice_dict = schemas.Invoice.model_validate(new_invoice).model_dump()
        return {"status": "success", "invoice_id": str(new_invoice.id), "data": make_model_dump_json_serializable(new_invoice_dict)}
    
    except KeyError as e:
        return {"status": "error", "message": f"Missing required argument from LLM for invoice creation: {str(e)}"}
    except ValueError as e: # For UUID conversion or Enum conversion errors
        return {"status": "error", "message": f"Invalid data format for invoice creation: {str(e)}"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to create invoice due to an unexpected error: {str(e)}"}


TOOL_EXECUTORS = {
    "get_customer_by_name": execute_get_customer_by_name,
    "create_customer_func": execute_create_customer_func,
    "update_customer_func": execute_update_customer_func,
    "get_item_by_name": execute_get_item_by_name,
    "create_item_func": execute_create_item_func,
    "create_invoice_func": execute_create_invoice_func,
}

# --- Orchestration Logic ---
async def process_user_message(
    db: AsyncSession,
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    current_user: models.User,
    active_organization: Optional[models.Organization]
) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    
    if not gemini_sdk_client:
        return "AI service is currently unavailable (client not initialized).", conversation_history, None
    if not active_organization:
        return "Please select an active organization first to use AI features.", conversation_history, None

    gemini_sdk_history: List[types.Content] = []
    for entry in conversation_history:
        role = entry.get("role")
        parts_data_list = entry.get("parts", [])
        if not isinstance(parts_data_list, list): parts_data_list = [parts_data_list]

        gemini_parts_for_content: List[types.Part] = []
        actual_gemini_role_for_history = role 

        for p_item in parts_data_list:
            if role == "user":
                text_content = p_item if isinstance(p_item, str) else p_item.get("text", "")
                if text_content: gemini_parts_for_content.append(types.Part.from_text(text=text_content))
                actual_gemini_role_for_history = "user"
            elif role == "model": # This is for the LLM's textual responses
                text_content = p_item if isinstance(p_item, str) else p_item.get("text", "")
                if text_content: gemini_parts_for_content.append(types.Part.from_text(text=text_content))
                actual_gemini_role_for_history = "model"
            elif role == "function_call_request": # Model's request to call a function
                if isinstance(p_item, dict) and "name" in p_item and "args" in p_item:
                    gemini_parts_for_content.append(types.Part.from_function_call(
                        name=p_item["name"], args=p_item["args"]
                    ))
                actual_gemini_role_for_history = "model" # The request to call comes from the model
            elif role == "function_call_response":
                # For history passed to client.chats.create(), we CANNOT use role "tool".
                # Option A: Omit these from initial history. LLM will re-evaluate.
                print(f"Skipping role '{role}' for client.chats.create() history: {p_item}")
                continue # Skip adding this part to gemini_sdk_history for create()
        
        if gemini_parts_for_content: # Only add if there are parts to add (relevant if continue was hit)
            if not gemini_parts_for_content and role == "function_call_response": 
                pass
            else:
                gemini_sdk_history.append(types.Content(role=actual_gemini_role_for_history, parts=gemini_parts_for_content))
        elif role != "function_call_response": 
             print(f"Warning: No parts created for history entry role '{role}', data: {entry}")


    # System instruction text, formatted dynamically per call
    system_instruction_text = f"""
    You are "ProVoice AI", an expert assistant for Dad's Invoice Pro.
    Your goal is to help the user manage their invoicing tasks by intelligently using the available tools.
    The current user is '{current_user.email}' and the active organization is '{active_organization.name}' (ID: {active_organization.id}).
    All actions you take will be within the context of this organization.

    Available tools include getting customer info, creating new customers, AND UPDATING EXISTING CUSTOMERS. 
    If a user asks to change details for an existing customer, use the 'update_customer_func' tool. You will need the customer's ID for this, so if you only have the name, use 'get_customer_by_name' first to find their ID.

    Workflow:
    1. Understand User's Goal.
    2. Check Existing Data: ALWAYS use tools like 'get_customer_by_name' or 'get_item_by_name' first.
    3. Ask Clarifying Questions: If info is missing, use 'ask_clarifying_question'. Be specific.
    4. Plan and Execute: Call tools sequentially if needed.
    5. Tool Usage: When you decide to use a tool, the system will detect it. Provide the function name and arguments clearly.
    6. Present Results: After a tool is executed, you'll receive its result. Summarize this for the user.
    7. Line Items: For invoices, collect description, quantity (units or cartons), and price (mandatory). price_per_type defaults to 'UNIT', can be 'CARTON'. unit_type defaults to 'pieces'.
    8. Currency: Confirm invoice currency (3-letter uppercase, e.g., USD). Default to USD.
    9. Notes: Payment terms, shipping info (not covered by specific fields like container_number) go into 'comments_notes'.
    10. Dates: Use 'YYYY-MM-DD' for tool calls. invoice_date defaults to today.

    Example:
    User: "Invoice for NewClient Inc."
    AI (tool call): get_customer_by_name(company_name="NewClient Inc.")
    (Result: Not Found)
    AI (ask_clarifying_question): "Customer 'NewClient Inc.' not found. To proceed, I need to create them. Can you provide their email (optional)?"

If a tool errors, inform user, ask to retry or provide different info. Be concise.
"""
    
    try:
        # Use client.aio.chats.create (synchronous on client.aio, returns async chat object)
        chat_session = gemini_sdk_client.aio.chats.create( 
            model=f"models/{settings.GEMINI_MODEL_NAME}", 
            history=gemini_sdk_history # Now this history should only contain "user" and "model" roles
        )
                                                     
        print(f"Sending to Gemini. SDK History length (for create): {len(gemini_sdk_history)}. Current user message: {user_message}")
        
        current_generation_config = types.GenerateContentConfig(
            tools=ALL_TOOLS,
            system_instruction=system_instruction_text if not gemini_sdk_history else None, 
            temperature=0.7,
        )
        
        response = await chat_session.send_message(
            user_message, # Pass content as the FIRST POSITIONAL ARGUMENT
            config=current_generation_config
        )
    except Exception as e:
        print(f"Error during Gemini chat session or send_message: {e}")
        traceback.print_exc()
        return "Sorry, I encountered an error trying to process your request with the AI service.", conversation_history, None
    
    ai_response_text = ""
    follow_up_question_for_user = None
    updated_history = list(conversation_history) 
    updated_history.append({"role": "user", "parts": [user_message]})

    current_response = response
    MAX_TOOL_ITERATIONS = 5 
    tool_iterations = 0

    while tool_iterations < MAX_TOOL_ITERATIONS:
        tool_iterations += 1

        if not current_response or not current_response.function_calls:
            try:
                ai_response_text = current_response.text
                if not any(h_entry.get("role") == "model" and h_entry.get("parts") == [ai_response_text] for h_entry in updated_history[-2:]):
                    updated_history.append({"role": "model", "parts": [ai_response_text]})
            except ValueError: 
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
            break 

        # Process the first function call if multiple are returned.
        fc_to_process = current_response.function_calls[0]
        tool_name = fc_to_process.name
        tool_args = dict(fc_to_process.args) 

        print(f"LLM wants to call tool: {tool_name} with args: {tool_args}")
        # Record *all* function call requests from this turn for history
        fc_requests_for_history = [{"name": fc.name, "args": dict(fc.args)} for fc in current_response.function_calls]
        if not any(h_entry.get("role") == "function_call_request" and h_entry.get("parts") == fc_requests_for_history for h_entry in updated_history[-2:]):
            updated_history.append({
                "role": "function_call_request", 
                "parts": fc_requests_for_history
            })

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
                updated_history.append({
                    "role": "function_call_response", # Our internal history records this
                    "parts": [{"name": tool_name, "response": tool_result}]
                })
            
            # This is where we send the TOOL's response back to the LLM
            function_response_part = types.Part.from_function_response(
                name=tool_name,
                response=tool_result 
            )
            
            print(f"Sending tool result back to Gemini for {tool_name}")
            try:
                # For send_message, when sending a tool response, pass the Part object (or list of Parts)
                current_response = await chat_session.send_message(
                    function_response_part, # <--- PASS THE PART DIRECTLY
                    config=current_generation_config 
                )
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