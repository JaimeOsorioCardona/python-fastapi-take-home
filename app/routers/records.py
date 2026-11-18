import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection
from psycopg.rows import DictRow

from app.db import get_conn
from app.repositories.coffee_repository import (
    ALLOWED_SUMMARY_GROUPS,
    CoffeeRecordRepository,
)
from app.schemas.filters import CoffeeFilterParams
from app.schemas.responses import (
    CoffeeRecordResponse,
    PaginatedResponse,
    SummaryItem,
    SummaryResponse,
)

router = APIRouter(prefix="/records", tags=["Coffee Records"])

Conn = Annotated[Connection[DictRow], Depends(get_conn)]


@router.get(
    "",
    response_model=PaginatedResponse[CoffeeRecordResponse],
    summary="List and filter coffee health records with pagination",
)
def list_records(
    conn: Conn,
    filters: Annotated[CoffeeFilterParams, Query()],
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page (max 100)"),
) -> PaginatedResponse[CoffeeRecordResponse]:
    """Retrieve coffee health records matching the optional filters with pagination."""
    repo = CoffeeRecordRepository(conn)
    rows, total = repo.find_records(filters=filters, page=page, page_size=page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    items = [CoffeeRecordResponse.model_validate(r) for r in rows]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Analytical summary grouped by a categorical attribute",
)
def get_summary(
    conn: Conn,
    filters: Annotated[CoffeeFilterParams, Query()],
    group_by: str = Query(
        "country",
        description=(
            "Grouping attribute: country, gender, sleep_quality, "
            "stress_level, occupation, health_issues"
        ),
    ),
) -> SummaryResponse:
    """Compute aggregate health metrics grouped by a categorical key."""
    if group_by not in ALLOWED_SUMMARY_GROUPS:
        allowed_str = ", ".join(sorted(ALLOWED_SUMMARY_GROUPS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid group_by '{group_by}'. Must be one of: {allowed_str}",
        )

    repo = CoffeeRecordRepository(conn)
    rows = repo.get_summary(filters=filters, group_by=group_by)
    items = [SummaryItem.model_validate(r) for r in rows]

    return SummaryResponse(
        group_by=group_by,
        total_groups=len(items),
        results=items,
    )


@router.get(
    "/{record_id}",
    response_model=CoffeeRecordResponse,
    summary="Get single coffee record by ID",
)
def get_record_by_id(
    record_id: int,
    conn: Conn,
) -> CoffeeRecordResponse:
    """Retrieve a single coffee record by its primary key ID."""
    repo = CoffeeRecordRepository(conn)
    record = repo.get_by_id(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coffee record with ID {record_id} not found",
        )
    return CoffeeRecordResponse.model_validate(record)
