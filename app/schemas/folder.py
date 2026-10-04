
from pydantic import BaseModel, Field, field_validator, model_validator


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_folder_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Folder name cannot be empty")

        return value


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_folder_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Folder name cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self