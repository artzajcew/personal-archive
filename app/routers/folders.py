
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extensions import connection

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.folder import FolderCreate, FolderUpdate


router = APIRouter(
    prefix="/folders",
    tags=["Folders"],
)


# =====================================================
# CREATE FOLDER
# =====================================================

@router.post("", status_code=status.HTTP_201_CREATED)
def create_folder(
    data: FolderCreate,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Создаёт новую папку."""

    if data.parent_folder_id is not None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM folders
                WHERE id = %s AND user_id = %s
                """,
                (data.parent_folder_id, current_user["id"]),
            )

            parent = cursor.fetchone()

        if parent is None:
            raise HTTPException(
                status_code=404,
                detail="Parent folder not found",
            )

    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO folders (user_id, parent_folder_id, name)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, parent_folder_id, name, created_at
            """,
            (
                current_user["id"],
                data.parent_folder_id,
                data.name,
            ),
        )

        folder = cursor.fetchone()

    db.commit()

    return {
        "message": "Folder created successfully",
        "folder": folder,
    }


# =====================================================
# GET ALL FOLDERS
# =====================================================

@router.get("")
def get_folders(
    parent_folder_id: int | None = Query(default=None, gt=0),
    root_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Возвращает папки текущего пользователя."""

    if root_only and parent_folder_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Cannot combine root_only and parent_folder_id",
        )

    with db.cursor() as cursor:

        if root_only:
            cursor.execute(
                """
                SELECT id, user_id, parent_folder_id, name, created_at
                FROM folders
                WHERE user_id = %s AND parent_folder_id IS NULL
                ORDER BY name, id
                """,
                (current_user["id"],),
            )

        elif parent_folder_id is not None:
            cursor.execute(
                """
                SELECT id, user_id, parent_folder_id, name, created_at
                FROM folders
                WHERE user_id = %s AND parent_folder_id = %s
                ORDER BY name, id
                """,
                (current_user["id"], parent_folder_id),
            )

        else:
            cursor.execute(
                """
                SELECT id, user_id, parent_folder_id, name, created_at
                FROM folders
                WHERE user_id = %s
                ORDER BY name, id
                """,
                (current_user["id"],),
            )

        folders = cursor.fetchall()

    return {
        "count": len(folders),
        "folders": folders,
    }


# =====================================================
# GET FOLDER BY ID
# =====================================================

@router.get("/{folder_id}")
def get_folder(
    folder_id: int,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Возвращает конкретную папку."""

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, user_id, parent_folder_id, name, created_at
            FROM folders
            WHERE id = %s AND user_id = %s
            """,
            (folder_id, current_user["id"]),
        )

        folder = cursor.fetchone()

    if folder is None:
        raise HTTPException(
            status_code=404,
            detail="Folder not found",
        )

    return {"folder": folder}


# =====================================================
# UPDATE FOLDER
# =====================================================

@router.patch("/{folder_id}")
def update_folder(
    folder_id: int,
    data: FolderUpdate,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Изменяет название или родительскую папку."""

    updates = data.model_dump(exclude_unset=True)

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, parent_folder_id
            FROM folders
            WHERE id = %s AND user_id = %s
            FOR UPDATE
            """,
            (folder_id, current_user["id"]),
        )

        existing_folder = cursor.fetchone()

    if existing_folder is None:
        raise HTTPException(
            status_code=404,
            detail="Folder not found",
        )

    # Проверяем нового родителя
    if "parent_folder_id" in updates:
        new_parent_id = updates["parent_folder_id"]

        if new_parent_id is not None:

            if new_parent_id == folder_id:
                raise HTTPException(
                    status_code=400,
                    detail="Folder cannot be its own parent",
                )

            with db.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM folders
                    WHERE id = %s AND user_id = %s
                    """,
                    (new_parent_id, current_user["id"]),
                )

                parent = cursor.fetchone()

            if parent is None:
                raise HTTPException(
                    status_code=404,
                    detail="Parent folder not found",
                )

            # Проверяем, что новый родитель
            # не является потомком перемещаемой папки
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    WITH RECURSIVE descendants AS (
                        SELECT id
                        FROM folders
                        WHERE parent_folder_id = %s
                          AND user_id = %s

                        UNION ALL

                        SELECT f.id
                        FROM folders f
                        INNER JOIN descendants d
                            ON f.parent_folder_id = d.id
                        WHERE f.user_id = %s
                    )
                    SELECT EXISTS (
                        SELECT 1
                        FROM descendants
                        WHERE id = %s
                    ) AS has_cycle
                    """,
                    (
                        folder_id,
                        current_user["id"],
                        current_user["id"],
                        new_parent_id,
                    ),
                )

                result = cursor.fetchone()

            if result["has_cycle"]:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move folder into its own descendant",
                )

    # Формируем запрос только из разрешённых полей
    allowed_fields = {"name", "parent_folder_id"}

    if not updates or not set(updates).issubset(allowed_fields):
        raise HTTPException(
            status_code=422,
            detail="No valid fields to update",
        )

    set_clause = ", ".join(
        f"{field} = %s" for field in updates
    )

    values = list(updates.values())
    values.extend([folder_id, current_user["id"]])

    with db.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE folders
            SET {set_clause}
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, parent_folder_id, name, created_at
            """,
            values,
        )

        updated_folder = cursor.fetchone()

    db.commit()

    return {
        "message": "Folder updated successfully",
        "folder": updated_folder,
    }


# =====================================================
# DELETE FOLDER
# =====================================================

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    current_user: dict = Depends(get_current_user),
    db: connection = Depends(get_db),
):
    """Удаляет папку и её вложенные папки."""

    with db.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM folders
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (folder_id, current_user["id"]),
        )

        deleted_folder = cursor.fetchone()

    if deleted_folder is None:
        raise HTTPException(
            status_code=404,
            detail="Folder not found",
        )

    db.commit()

    return None