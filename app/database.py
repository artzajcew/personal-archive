
from collections.abc import Generator

import psycopg2
from fastapi import HTTPException
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from app.config import settings


def get_connection() -> connection:
    """Создаёт подключение к PostgreSQL."""

    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        cursor_factory=RealDictCursor,
        connect_timeout=5,
    )


def get_db() -> Generator[connection, None, None]:
    """Предоставляет подключение для обработки HTTP-запроса."""

    try:
        db = get_connection()
    except psycopg2.OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Database is currently unavailable"
        )

    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
