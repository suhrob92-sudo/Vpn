"""Standard API response envelope."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: dict[str, Any] | None = None


def ok(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}


def err(code: str, message: str) -> dict:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}
