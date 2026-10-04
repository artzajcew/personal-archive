
import psycopg2

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.extensions import connection

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.tag import TagCreate, TagUpdate


router = APIRouter(tags=["Tags"])


@router.post(
    "/tags",
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    data: TagCreate,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tags (user_id, name)
                VALUES (%s, %s)
                RETURNING id, name
                """,
                (user_id, data.name)
            )

            tag = cursor.fetchone()

        db.commit()

        return dict(tag)

    except psycopg2.errors.UniqueViolation:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists"
        )


@router.get("/tags")
def get_tags(
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                t.id,
                t.name,
                COUNT(it.item_id) AS items_count
            FROM tags t
            LEFT JOIN item_tags it
                ON it.tag_id = t.id
                AND it.user_id = t.user_id
            WHERE t.user_id = %s
            GROUP BY t.id, t.name
            ORDER BY t.name
            """,
            (current_user["id"],)
        )

        tags = [dict(row) for row in cursor.fetchall()]

    return tags


@router.patch("/tags/{tag_id}")
def update_tag(
    tag_id: int,
    data: TagUpdate,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tags
                SET name = %s
                WHERE id = %s AND user_id = %s
                RETURNING id, name
                """,
                (data.name, tag_id, current_user["id"])
            )

            tag = cursor.fetchone()

        if tag is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )

        db.commit()

        return dict(tag)

    except psycopg2.errors.UniqueViolation:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists"
        )


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_tag(
    tag_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM tags
            WHERE id = %s AND user_id = %s
            RETURNING id
            """,
            (tag_id, current_user["id"])
        )

        deleted_tag = cursor.fetchone()

    if deleted_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    db.commit()


@router.get("/items/{item_id}/tags")
def get_item_tags(
    item_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM archive_items
            WHERE id = %s AND user_id = %s
            """,
            (item_id, current_user["id"])
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archive item not found"
            )

        cursor.execute(
            """
            SELECT t.id, t.name
            FROM tags t
            JOIN item_tags it ON it.tag_id = t.id
            WHERE it.item_id = %s
              AND it.user_id = %s
            ORDER BY t.name
            """,
            (item_id, current_user["id"])
        )

        tags = [dict(row) for row in cursor.fetchall()]

    return tags


@router.post(
    "/items/{item_id}/tags/{tag_id}",
    status_code=status.HTTP_201_CREATED
)
def attach_tag(
    item_id: int,
    tag_id: int,
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
            """,
            (item_id, user_id)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archive item not found"
            )

        cursor.execute(
            """
            SELECT id
            FROM tags
            WHERE id = %s AND user_id = %s
            """,
            (tag_id, user_id)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )

        cursor.execute(
            """
            INSERT INTO item_tags (item_id, tag_id, user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (item_id, tag_id) DO NOTHING
            """,
            (item_id, tag_id, user_id)
        )

    db.commit()

    return {
        "message": "Tag attached successfully",
        "item_id": item_id,
        "tag_id": tag_id
    }


@router.delete(
    "/items/{item_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def detach_tag(
    item_id: int,
    tag_id: int,
    db: connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM item_tags
            WHERE item_id = %s
                AND tag_id = %s
                AND user_id = %s
            RETURNING item_id
            """,
            (item_id, tag_id, current_user["id"])
        )

        deleted_relation = cursor.fetchone()

    if deleted_relation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag relation not found"
        )

    db.commit()