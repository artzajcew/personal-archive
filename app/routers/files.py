import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from psycopg2.extensions import connection

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/files",
    tags=["Files"]
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".txt",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_file(filename: str) -> str:
    extension = get_extension(filename)

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed"
        )

    return extension


def get_upload_path() -> Path:
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post(
    "/{item_id}",
    status_code=status.HTTP_201_CREATED
)
async def upload_file(
    item_id: int,
    file: UploadFile = File(...),
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )

    extension = validate_file(file.filename)

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                file_path
            FROM archive_items
            WHERE id = %s AND user_id = %s
            """,
            (item_id, user_id)
        )

        item = cursor.fetchone()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive item not found"
        )

    upload_dir = get_upload_path()

    random_name = f"{uuid.uuid4().hex}{extension}"
    file_path = upload_dir / random_name

    total_size = 0

    try:
        with open(file_path, "wb") as output_file:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > settings.MAX_FILE_SIZE:
                    output_file.close()

                    if file_path.exists():
                        file_path.unlink()

                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File is too large"
                    )

                output_file.write(chunk)

        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE archive_items
                SET
                    file_path = %s,
                    original_file_name = %s,
                    file_size = %s,
                    mime_type = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                RETURNING
                    id,
                    title,
                    original_file_name,
                    file_size,
                    mime_type,
                    file_path
                """,
                (
                    str(file_path),
                    file.filename,
                    total_size,
                    file.content_type,
                    item_id,
                    user_id
                )
            )

            updated_item = cursor.fetchone()

        db.commit()

        return dict(updated_item)

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )

    finally:
        await file.close()


@router.get("/{item_id}")
def download_file(
    item_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                file_path,
                original_file_name,
                mime_type
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

    if not item["file_path"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This archive item has no file"
        )

    file_path = Path(item["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )

    return FileResponse(
        path=file_path,
        media_type=item["mime_type"] or "application/octet-stream",
        filename=item["original_file_name"] or file_path.name
    )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_file(
    item_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT file_path
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

    if not item["file_path"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This archive item has no file"
        )

    file_path = Path(item["file_path"])

    if file_path.exists():
        file_path.unlink()

    with db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE archive_items
            SET
                file_path = NULL,
                original_file_name = NULL,
                file_size = NULL,
                mime_type = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (item_id, current_user["id"])
        )

    db.commit()