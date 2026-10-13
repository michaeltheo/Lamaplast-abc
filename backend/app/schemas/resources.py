from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import RESOURCE_TYPES
from app.schemas.common import AuditedOut, NotesText, OrmOut, PatchModel

ResourceType = Literal[*RESOURCE_TYPES]


class ResourceCreate(BaseModel):
    Resource_Code: str = Field(min_length=1, max_length=20)
    Resource_Name: str = Field(min_length=1, max_length=80)
    CC_ID: int
    Resource_Type: ResourceType
    Notes: NotesText | None = None


class ResourceUpdate(PatchModel):
    required_fields = frozenset({"Resource_Code", "Resource_Name", "CC_ID", "Resource_Type"})

    Resource_Code: str | None = Field(default=None, min_length=1, max_length=20)
    Resource_Name: str | None = Field(default=None, min_length=1, max_length=80)
    CC_ID: int | None = None
    Resource_Type: ResourceType | None = None
    Notes: NotesText | None = None


class ResourceOut(AuditedOut):
    Resource_ID: int
    Resource_Code: str
    Resource_Name: str
    CC_ID: int
    Resource_Type: str
    Is_Active: bool
    Notes: str | None


# --- ποσοστά πόρου ανά δραστηριότητα (σε ένα σενάριο) ---

class ActivityShareIn(BaseModel):
    Activity_ID: int
    Share_Pct: Decimal = Field(gt=0, le=1, max_digits=7, decimal_places=6)   # 0.80 = 80%
    Allocation_Basis: str | None = Field(default=None, max_length=80)
    Notes: NotesText | None = None


class ActivityShareOut(OrmOut):
    Scenario_ID: int
    Resource_ID: int
    Activity_ID: int
    Share_Pct: Decimal
    Allocation_Basis: str | None
    Notes: str | None


class AllocationIssueOut(BaseModel):
    """Πόρος που δεν είναι έτοιμος για υπολογισμό: χωρίς ποσοστά ή με άθροισμα ≠ 100%."""
    Resource_ID: int
    Resource_Code: str
    Resource_Name: str
    Resource_Type: str
    Activities: int
    Total_Share_Pct: Decimal
    Message: str
