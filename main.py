from collections.abc import Generator

import psycopg2
from fastapi import Depends, FastAPI, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_connection


app = FastAPI(title="Personal Archive API")


def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
	connection = get_connection()
	if connection is None:
		raise HTTPException(status_code=503, detail="Database is unavailable")

	try:
		yield connection
	finally:
		connection.close()


@app.get("/files")
def list_files(
	user_id: int | None = None,
	connection: psycopg2.extensions.connection = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
	query = """
		SELECT id, user_id, folder_id, title, item_type, description,
		        content, file_path, created_at, updated_at
		FROM archive_items
	"""
	with connection.cursor(cursor_factory=RealDictCursor) as cursor:
		if user_id is None:
			cursor.execute(query + " ORDER BY created_at DESC, id DESC")
		else:
			cursor.execute(
				query + " WHERE user_id = %s ORDER BY created_at DESC, id DESC",
				(user_id,),
			)
		rows = cursor.fetchall()

	return {"files": rows}

