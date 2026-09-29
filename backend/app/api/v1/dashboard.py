from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.dashboard import DashboardRead
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def get_dashboard(
    internship_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardRead:
    if internship_id is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Internship filter is only available to administrators"
        )
    try:
        return DashboardService.build(db, current_user, internship_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
