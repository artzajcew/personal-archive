
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from psycopg2 import errors
from psycopg2.extensions import connection
from pwdlib import PasswordHash

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user, security
from app.schemas.auth import (
    PasswordChange,
    UserLogin,
    UserProfileUpdate,
    UserRegister,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

password_hash = PasswordHash.recommended()


def create_access_token(
    user_id: int,
    token_version: int
) -> tuple[str, str, datetime]:
    """Создаёт JWT-токен."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token_id = str(uuid4())

    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "ver": token_version,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token, token_id, expires_at


# =====================================================
# REGISTER
# =====================================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegister,
    db: connection = Depends(get_db),
):
    """Регистрирует нового пользователя."""

    hashed_password = password_hash.hash(data.password)

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, username, email, created_at
                """,
                (
                    data.username,
                    str(data.email).lower(),
                    hashed_password,
                ),
            )

            user = cursor.fetchone()

        db.commit()

        return {
            "message": "Registration successful",
            "user": user,
        }

    except errors.UniqueViolation:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Username or email is already registered",
        )


# =====================================================
# LOGIN
# =====================================================

@router.post("/login")
def login(
    data: UserLogin,
    db: connection = Depends(get_db),
):
    """Авторизует пользователя и выдаёт JWT."""

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, password_hash, token_version
            FROM users
            WHERE LOWER(username) = LOWER(%s)
               OR LOWER(email) = LOWER(%s)
            """,
            (data.identifier.strip(), data.identifier.strip()),
        )

        user = cursor.fetchone()

    if user is None or not password_hash.verify(
        data.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, _, expires_at = create_access_token(
        user["id"],
        user["token_version"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
    }


# =====================================================
# LOGOUT
# =====================================================

@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Отзывает текущий JWT."""

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_id = payload["jti"]
        expires_at = datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc,
        )

    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO revoked_tokens (jti, expires_at)
            VALUES (%s, %s)
            ON CONFLICT (jti) DO NOTHING
            """,
            (token_id, expires_at),
        )

    db.commit()

    return {"message": "Successfully logged out"}


# =====================================================
# GET CURRENT USER
# =====================================================

@router.get("/me")
def get_profile(
    current_user: dict = Depends(get_current_user),
):
    """Возвращает профиль текущего пользователя."""

    return {"user": current_user}


# =====================================================
# UPDATE PROFILE
# =====================================================

@router.patch("/me")
def update_profile(
    data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Изменяет username и/или email."""

    updates = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    allowed_fields = {"username", "email"}

    if not updates or not set(updates).issubset(allowed_fields):
        raise HTTPException(
            status_code=422,
            detail="No valid fields to update",
        )

    if "email" in updates:
        updates["email"] = str(updates["email"]).lower()

    set_clause = ", ".join(
        f"{field} = %s" for field in updates
    )

    values = list(updates.values())
    values.append(current_user["id"])

    try:
        with db.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE users
                SET {set_clause}
                WHERE id = %s
                RETURNING id, username, email, created_at
                """,
                values,
            )

            updated_user = cursor.fetchone()

        db.commit()

        return {
            "message": "Profile updated successfully",
            "user": updated_user,
        }

    except errors.UniqueViolation:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Username or email is already taken",
        )


# =====================================================
# CHANGE PASSWORD
# =====================================================

@router.patch("/password")
def change_password(
    data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Изменяет пароль пользователя."""

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = %s",
            (current_user["id"],),
        )

        user = cursor.fetchone()

    if not password_hash.verify(
        data.current_password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    new_hash = password_hash.hash(data.new_password)

    with db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s,
                token_version = token_version + 1
            WHERE id = %s
            """,
            (new_hash, current_user["id"]),
        )

    db.commit()

    return {
        "message": "Password changed successfully. Please log in again."
    }


# =====================================================
# DELETE ACCOUNT
# =====================================================

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Удаляет аккаунт и связанные с ним данные."""

    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM users WHERE id = %s",
            (current_user["id"],),
        )

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
