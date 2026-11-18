from collections.abc import Iterator

from fastapi import HTTPException, Request, status
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.config import settings

Pool = ConnectionPool[Connection[DictRow]]


def create_pool() -> Pool:
    """Create and open a connection pool. Called once per app lifespan."""
    pool: Pool = ConnectionPool(
        settings.database_url,
        connection_class=Connection[DictRow],
        kwargs={
            "row_factory": dict_row,
            "options": "-c statement_timeout=5000",
        },
        min_size=2,
        max_size=10,
        timeout=5.0,
        open=False,
    )
    pool.open(wait=True)
    return pool


def get_conn(request: Request) -> Iterator[Connection[DictRow]]:
    """FastAPI dependency that borrows a connection from the pool for one request."""
    pool: Pool = request.app.state.pool
    try:
        with pool.connection(timeout=5.0) as conn:
            yield conn
    except PoolTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection pool exhausted. Please retry shortly.",
            headers={"Retry-After": "1"},
        ) from exc
