# backend/app/api/endpoints/chat.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel # <--- IMPORT BaseModel directly from pydantic


from app import models, crud # For current_user, active_organization
from app.db.session import get_db
from app.api import deps
from app.services.ai_orchestrator import process_user_message # Our new service

router = APIRouter()

class ChatRequest(BaseModel): # <--- USE BaseModel directly
    message: str
    history: Optional[List[Dict[str, Any]]] = []


class ChatResponse(BaseModel): # <--- USE BaseModel directly
    reply: str
    history: List[Dict[str, Any]]
    follow_up_question: Optional[str] = None
    # session_id: Optional[str] = None

@router.post("/", response_model=ChatResponse)
async def handle_chat_message(
    request_data: ChatRequest, # Use Pydantic model for request body
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    # How to get active_organization?
    # Option 1: Client sends active_organization_id with each chat message (less ideal)
    # Option 2: Store active_organization_id in user's session/token (more involved for stateless API)
    # Option 3: For now, let's assume the orchestrator or a dependency can fetch it
    #           or we require it to be passed.
    # Let's try fetching the user's *first* organization if multiple, or require client to specify.
    # For simplicity, we'll try to get the first one or one marked as 'active' if you implement that.
    # A robust solution might involve a header or a field in ChatRequest for current org context.
):
    """
    Handles a user's chat message, interacts with the AI orchestrator,
    and returns the AI's response.
    """
    # Simplified: Try to get an active organization for the user.
    # In a real app, the frontend context (useOrg) would determine this.
    # For the API, you might need the client to send an `active_organization_id`
    # or have a default/last-used mechanism.
    
    # Let's assume for now that the orchestrator will handle the "no active org" case if necessary,
    # or that the user context somehow implies it.
    # For a direct test, we might need to fetch one or pass one in.
    
    # TEMPORARY: Fetch the first organization for the user to act as active context.
    # This is a placeholder. In a real scenario, the client should specify the active org context.
    user_orgs = await crud.organization.get_organizations_by_user(db, user_id=current_user.id, limit=1)
    active_org_model: Optional[models.Organization] = None
    if user_orgs:
        active_org_model = await crud.organization.get_organization(db, org_id=user_orgs[0].id) # Fetch full model


    if not active_org_model:
         # If you require an org context for all AI chat operations:
         # raise HTTPException(status_code=400, detail="No active organization context available for AI chat. Please select an organization.")
         # Or let the orchestrator handle this scenario gracefully.
         pass # Orchestrator will check and respond appropriately

    ai_reply, updated_history, followup_q = await process_user_message(
        db=db,
        user_message=request_data.message,
        conversation_history=request_data.history or [],
        current_user=current_user,
        active_organization=active_org_model # Pass the fetched org model
    )

    return ChatResponse(
        reply=ai_reply,
        history=updated_history,
        follow_up_question=followup_q
    )