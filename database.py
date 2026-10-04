import psycopg2
from psycopg2 import OperationalError

# Данные для подключения к PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "archive",
    "user": "postgres",
    "password": "1234",
}


def get_connection():
    """Создаёт и возвращает подключение к базе данных."""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        print("Подключение к базе данных успешно!")
        return connection
    except OperationalError as error:
        print("Ошибка подключения к базе данных:")
        print(error)
        return None


if __name__ == "__main__":
    connection = get_connection()

    if connection:
        connection.close()
        print("Подключение закрыто.")
