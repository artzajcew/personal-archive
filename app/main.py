
from fastapi import FastAPI, HTTPException
from psycopg2 import OperationalError

from app.database import get_connection
from app.routers.auth import router as auth_router
from app.routers.folders import router as folders_router
from app.routers.tags import router as tags_router
from app.routers.items import router as items_router
from app.routers.files import router as files_router

app = FastAPI(
    title="Chronikle API",
    description="Personal Digital Archive API",
    version="1.0.0",
)

# Подключаем авторизацию
app.include_router(auth_router)
app.include_router(folders_router)
app.include_router(tags_router)
app.include_router(items_router)
app.include_router(files_router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "application": "Chronikle API",
    }


@app.get("/health/database", tags=["System"])
def database_health_check():
    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return {
            "status": "ok",
            "database": "connected",
        }

    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )

    finally:
        if connection is not None:
            connection.close()