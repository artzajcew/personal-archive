
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from psycopg2.extensions import connection

from app.config import settings
from app.database import get_db


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: connection = Depends(get_db),
) -> dict:
    """Проверяет JWT и возвращает текущего пользователя."""

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id = int(payload["sub"])
        token_id = payload["jti"]
        token_version = int(payload["ver"])

    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM revoked_tokens
            WHERE jti = %s
            """,
            (token_id,),
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked",
            )

        cursor.execute(
            """
            SELECT id, username, email, created_at, token_version
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )

        user = cursor.fetchone()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if user["token_version"] != token_version:
        raise HTTPException(
            status_code=401,
            detail="Session has expired. Please log in again.",
        )

    user.pop("token_version")

    return user
