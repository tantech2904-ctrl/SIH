from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str | None = None
    details: dict | None = None