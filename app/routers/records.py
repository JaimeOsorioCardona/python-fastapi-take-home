import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection
from psycopg.rows import DictRow

from app.db import get_conn
from app.repositories.coffee_repository import (
    ALLOWED_SUMMARY_GROUPS,
    CoffeeRecordRepository,
    decode_cursor,
    encode_cursor,
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
    summary="List and filter coffee health records with offset or keyset pagination",
)
def list_records(
    conn: Conn,
    filters: Annotated[CoffeeFilterParams, Query()],
    page: int = Query(1, ge=1, description="Page number for offset pagination (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page (max 100)"),
    cursor: str | None = Query(
        default=None,
        description="Optional opaque base64 cursor for high-performance keyset pagination",
    ),
) -> PaginatedResponse[CoffeeRecordResponse]:
    """Retrieve coffee health records matching filters.

    Supports both:
    1. Standard offset/limit pagination (page, page_size) with total counts.
    2. Keyset cursor pagination (cursor, page_size) operating in constant O(1) time at scale.
    """
    repo = CoffeeRecordRepository(conn)

    # 1. Keyset cursor-based pagination
    if cursor is not None:
        try:
            cursor_id = decode_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid pagination cursor: {exc}",
            ) from exc

        rows, next_cursor, has_next = repo.find_records_cursor(
            filters=filters, cursor_id=cursor_id, limit=page_size
        )
        items = [CoffeeRecordResponse.model_validate(r) for r in rows]

        return PaginatedResponse(
            items=items,
            total=None,
            page=None,
            page_size=page_size,
            total_pages=None,
            has_next=has_next,
            has_previous=True,
            next_cursor=next_cursor,
        )

    # 2. Standard offset-based pagination
    rows, total = repo.find_records(filters=filters, page=page, page_size=page_size)

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    items = [CoffeeRecordResponse.model_validate(r) for r in rows]
    has_next = page < total_pages
    next_cur = encode_cursor(items[-1].id) if (has_next and items) else None

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=page > 1,
        next_cursor=next_cur,
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
