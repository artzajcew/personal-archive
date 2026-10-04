
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extensions import connection

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.item import ArchiveItemCreate, ArchiveItemUpdate


router = APIRouter(
    prefix="/items",
    tags=["Archive Items"]
)


ItemType = Literal["document", "photo", "note", "other"]


def check_folder_access(
    db: connection,
    folder_id: int,
    user_id: int
) -> None:
    """Проверяет, принадлежит ли папка текущему пользователю."""

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM folders
            WHERE id = %s AND user_id = %s
            """,
            (folder_id, user_id)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def create_item(
    data: ArchiveItemCreate,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    if data.folder_id is not None:
        check_folder_access(db, data.folder_id, user_id)

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO archive_items (
                user_id,
                folder_id,
                title,
                item_type,
                description,
                content
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                title,
                item_type,
                description,
                content,
                folder_id,
                created_at,
                updated_at
            """,
            (
                user_id,
                data.folder_id,
                data.title,
                data.item_type,
                data.description,
                data.content
            )
        )

        item = cursor.fetchone()

    db.commit()

    return dict(item)


@router.get("")
def get_items(
    q: str | None = Query(default=None, max_length=200),
    folder_id: int | None = Query(default=None, gt=0),
    root_only: bool = False,
    item_type: ItemType | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    if folder_id is not None and root_only:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either folder_id or root_only, not both"
        )

    if folder_id is not None:
        check_folder_access(db, folder_id, user_id)

    conditions = ["user_id = %s"]
    params = [user_id]

    if folder_id is not None:
        conditions.append("folder_id = %s")
        params.append(folder_id)

    elif root_only:
        conditions.append("folder_id IS NULL")

    if item_type is not None:
        conditions.append("item_type = %s")
        params.append(item_type)

    if q and q.strip():
        search = f"%{q.strip()}%"
        conditions.append(
            """
            (
                title ILIKE %s
                OR description ILIKE %s
                OR content ILIKE %s
            )
            """
        )
        params.extend([search, search, search])

    where_clause = " AND ".join(conditions)

    with db.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM archive_items
            WHERE {where_clause}
            """,
            tuple(params)
        )

        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT
                id,
                title,
                item_type,
                description,
                content,
                folder_id,
                created_at,
                updated_at
            FROM archive_items
            WHERE {where_clause}
            ORDER BY updated_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        items = [dict(row) for row in cursor.fetchall()]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{item_id}")
def get_item(
    item_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                title,
                item_type,
                description,
                content,
                folder_id,
                created_at,
                updated_at
            FROM archive_items
            WHERE id = %s AND user_id = %s
            """,
            (item_id, current_user["id"])
        )

        item = cursor.fetchone()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive item not found"
        )

    return dict(item)


@router.patch("/{item_id}")
def update_item(
    item_id: int,
    data: ArchiveItemUpdate,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM archive_items
            WHERE id = %s AND user_id = %s
            FOR UPDATE
            """,
            (item_id, user_id)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archive item not found"
            )

    updates = data.model_dump(exclude_unset=True)

    if "folder_id" in updates and updates["folder_id"] is not None:
        check_folder_access(db, updates["folder_id"], user_id)

    allowed_fields = {
        "title",
        "item_type",
        "folder_id",
        "description",
        "content"
    }

    set_parts = []
    values = []

    for field, value in updates.items():
        if field not in allowed_fields:
            continue

        set_parts.append(f"{field} = %s")
        values.append(value)

    set_parts.append("updated_at = CURRENT_TIMESTAMP")

    values.extend([item_id, user_id])

    query = f"""
        UPDATE archive_items
        SET {", ".join(set_parts)}
        WHERE id = %s AND user_id = %s
        RETURNING
            id,
            title,
            item_type,
            description,
            content,
            folder_id,
            created_at,
            updated_at
    """

    with db.cursor() as cursor:
        cursor.execute(query, tuple(values))
        item = cursor.fetchone()

    db.commit()

    return dict(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_item(
    item_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM archive_items
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (item_id, current_user["id"])
        )

        deleted_item = cursor.fetchone()

    if deleted_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive item not found"
        )

    db.commit()
