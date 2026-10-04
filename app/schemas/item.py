
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ItemType = Literal["document", "photo", "note", "other"]


class ArchiveItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    item_type: ItemType
    folder_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=2000)
    content: str | None = Field(default=None, max_length=1_000_000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Title cannot be empty")

        return value


class ArchiveItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    item_type: ItemType | None = None
    folder_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=2000)
    content: str | None = Field(default=None, max_length=1_000_000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Title cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null")

        if "item_type" in self.model_fields_set and self.item_type is None:
            raise ValueError("Item type cannot be null")

        return self
