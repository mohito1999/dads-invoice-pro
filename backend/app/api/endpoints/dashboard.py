from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from datetime import date

from app import crud, models, schemas # schemas for DashboardStats & DashboardFilters
from app.db.session import get_db
from app.api import deps # For get_current_active_user

router = APIRouter()

@router.get("/stats", response_model=schemas.DashboardStats)
async def get_user_dashboard_stats(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    # Use Depends for query parameters to leverage Pydantic validation from DashboardFilters
    filters: schemas.DashboardFilters = Depends() 
    # organization_id: Optional[uuid.UUID] = Query(None, description="Filter stats by a specific organization ID"),
    # date_from: Optional[date] = Query(None, description="Start date for stats (YYYY-MM-DD)"),
    # date_to: Optional[date] = Query(None, description="End date for stats (YYYY-MM-DD)")
):
    """
    Retrieve dashboard statistics for the authenticated user.
    Stats can be filtered by organization_id and date range.
    """
    # The 'filters' object now contains organization_id, date_from, date_to
    # as validated by Pydantic.
    
    # Optional: If organization_id is provided in filters,
    # you might want to double-check user ownership of that org here,
    # though crud.dashboard.get_dashboard_stats also filters by user_id implicitly.
    if filters.organization_id:
         org = await crud.organization.get_organization(db, org_id=filters.organization_id)
         if not org or org.user_id != current_user.id:
             raise HTTPException(status_code=403, detail="Not authorized for this organization's stats")

    stats_data = await crud.dashboard.get_dashboard_stats(
        db,
        user_id=current_user.id,
        organization_id=filters.organization_id,
        date_from=filters.date_from,
        date_to=filters.date_to
    )
    return stats_data # Pydantic will validate this dict against DashboardStats schema