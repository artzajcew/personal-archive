
import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "archive")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE = int(
        os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024))
    )

    def validate(self):
        required_settings = {
            "DB_PASSWORD": self.DB_PASSWORD,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY
        }

        missing = [
            name
            for name, value in required_settings.items()
            if not value
        ]

        if missing:
            raise ValueError(
                f"Missing required settings: {', '.join(missing)}"
            )


settings = Settings()
settings.validate()
