from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ASSEMBLY_TYPES
from app.schemas.common import AuditedOut, NotesText, PatchModel

OperationType = Literal[*ASSEMBLY_TYPES]


class AssemblyOpCreate(BaseModel):
    AssemblyOp_Code: str = Field(min_length=1, max_length=20)
    Item_ID: int
    Operation_Name: str = Field(min_length=1, max_length=100)
    Activity_ID: int | None = None
    Operation_Type: OperationType = "OWN"
    Workers_Per_Cell: Decimal = Field(default=Decimal(1), gt=0, max_digits=5, decimal_places=2)
    Units_Per_Hour: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    Sequence: int = Field(default=10, ge=0, le=32767)
    Notes: NotesText | None = None


class AssemblyOpUpdate(PatchModel):
    required_fields = frozenset({"AssemblyOp_Code", "Item_ID", "Operation_Name", "Operation_Type",
                                 "Workers_Per_Cell", "Units_Per_Hour", "Sequence"})

    AssemblyOp_Code: str | None = Field(default=None, min_length=1, max_length=20)
    Item_ID: int | None = None
    Operation_Name: str | None = Field(default=None, min_length=1, max_length=100)
    Activity_ID: int | None = None
    Operation_Type: OperationType | None = None
    Workers_Per_Cell: Decimal | None = Field(default=None, gt=0, max_digits=5, decimal_places=2)
    Units_Per_Hour: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    Sequence: int | None = Field(default=None, ge=0, le=32767)
    Notes: NotesText | None = None


class AssemblyOpOut(AuditedOut):
    AssemblyOp_ID: int
    AssemblyOp_Code: str
    Item_ID: int
    Operation_Name: str
    Activity_ID: int | None
    Operation_Type: str
    Workers_Per_Cell: Decimal
    Units_Per_Hour: Decimal
    Sec_Per_Unit: Decimal            # υπολογίζεται από τη βάση
    Labor_Hrs_Per_Unit: Decimal      # υπολογίζεται από τη βάση
    Sequence: int
    Is_Active: bool
    Notes: str | None
