
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Username cannot be empty")

        if not all(
            char.isalnum() or char in "_.-"
            for char in value
        ):
            raise ValueError(
                "Username can contain only letters, digits, _, . and -"
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserLogin(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value or not all(
            char.isalnum() or char in "_.-"
            for char in value
        ):
            raise ValueError("Invalid username")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None

        return str(value).strip().lower()

    @model_validator(mode="after")
    def check_fields(self):
        if self.username is None and self.email is None:
            raise ValueError("At least one field must be provided")

        return self


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_passwords(self):
        if self.current_password == self.new_password:
            raise ValueError(
                "New password must differ from current password"
            )

        return self
