from pydantic import BaseModel, Field

from app.schemas.common import AuditedOut, NotesText, PatchModel


class CustomerCreate(BaseModel):
    Customer_Code: str = Field(min_length=1, max_length=10)
    Customer_Name: str = Field(min_length=1, max_length=100)
    Is_Internal: bool = False
    Notes: NotesText | None = None


class CustomerUpdate(PatchModel):
    required_fields = frozenset({"Customer_Code", "Customer_Name", "Is_Internal"})

    Customer_Code: str | None = Field(default=None, min_length=1, max_length=10)
    Customer_Name: str | None = Field(default=None, min_length=1, max_length=100)
    Is_Internal: bool | None = None
    Notes: NotesText | None = None


class CustomerOut(AuditedOut):
    Customer_ID: int
    Customer_Code: str
    Customer_Name: str
    Is_Internal: bool
    Is_Active: bool
    Notes: str | None
