from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    status_code: int
    success: bool
    message: str | None = None
    data: T | None = None


class FieldError(BaseModel):
    field: str
    message: str
