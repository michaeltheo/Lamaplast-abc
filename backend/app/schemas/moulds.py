from datetime import date
from decimal import Decimal
from typing import Literal

from app.models.enums import MOULD_OWNERS, MOULD_TYPES
from app.schemas.common import AuditedOut, Money, NotesText, PatchModel
from pydantic import BaseModel, Field, computed_field

MouldOwner = Literal[*MOULD_OWNERS]
MouldType = Literal[*MOULD_TYPES]


class MouldCreate(BaseModel):
    Mould_Code: str = Field(min_length=1, max_length=20)
    Mould_Name: str = Field(min_length=1, max_length=100)
    Item_ID: int | None = None
    Mould_Owner: MouldOwner = "LAMAPLAST"
    Customer_ID: int | None = None
    Mould_Type: MouldType = "SINGLE"
    Cavities: int = Field(default=1, ge=1, le=32767)
    Default_Machine_Category: str | None = Field(default=None, max_length=5)
    Acquisition_Cost_EUR: Money = Decimal(0)
    Residual_Value_EUR: Money = Decimal(0)
    Life_Cycles: int | None = Field(default=None, gt=0, le=2_000_000_000)
    Current_Cycles: int = Field(default=0, ge=0, le=2_000_000_000)
    QC_Factor: int = Field(default=2, ge=1, le=3)
    Technicians: int | None = Field(default=None, ge=0, le=32767)
    Year_Constructed: int | None = Field(default=None, ge=1900, le=2100)
    Replacement_Estimate: date | None = None
    Notes: NotesText | None = None


class MouldUpdate(PatchModel):
    required_fields = frozenset({"Mould_Code", "Mould_Name", "Mould_Owner", "Mould_Type", "Cavities",
                                 "Acquisition_Cost_EUR", "Residual_Value_EUR", "Current_Cycles", "QC_Factor"})

    Mould_Code: str | None = Field(default=None, min_length=1, max_length=20)
    Mould_Name: str | None = Field(default=None, min_length=1, max_length=100)
    Item_ID: int | None = None
    Mould_Owner: MouldOwner | None = None
    Customer_ID: int | None = None
    Mould_Type: MouldType | None = None
    Cavities: int | None = Field(default=None, ge=1, le=32767)
    Default_Machine_Category: str | None = Field(default=None, max_length=5)
    Acquisition_Cost_EUR: Money | None = None
    Residual_Value_EUR: Money | None = None
    Life_Cycles: int | None = Field(default=None, gt=0, le=2_000_000_000)
    Current_Cycles: int | None = Field(default=None, ge=0, le=2_000_000_000)
    QC_Factor: int | None = Field(default=None, ge=1, le=3)
    Technicians: int | None = Field(default=None, ge=0, le=32767)
    Year_Constructed: int | None = Field(default=None, ge=1900, le=2100)
    Replacement_Estimate: date | None = None
    Notes: NotesText | None = None


class MouldOut(AuditedOut):
    Mould_ID: int
    Mould_Code: str
    Mould_Name: str
    Item_ID: int | None
    Mould_Owner: str
    Customer_ID: int | None
    Mould_Type: str
    Cavities: int
    Default_Machine_Category: str | None
    Acquisition_Cost_EUR: Decimal
    Residual_Value_EUR: Decimal
    Depreciable_Value_EUR: Decimal            # υπολογίζεται από τη βάση
    Life_Cycles: int | None
    Current_Cycles: int
    Wear_Pct: Decimal | None                  # υπολογίζεται από τη βάση
    Depreciation_Per_Cycle: Decimal | None    # υπολογίζεται από τη βάση
    QC_Factor: int
    Technicians: int | None
    Year_Constructed: int | None
    Replacement_Estimate: date | None
    Is_Active: bool
    Notes: str | None

    @computed_field
    @property
    def warnings(self) -> list[str]:
        """Δεν μπλοκάρουν την αποθήκευση· το UI τα δείχνει δίπλα στο καλούπι."""
        if self.Life_Cycles is not None and self.Current_Cycles > self.Life_Cycles:
            return [f"Το καλούπι έχει ξεπεράσει τη διάρκεια ζωής του ({self.Current_Cycles} κύκλοι "
                    + f"από {self.Life_Cycles})"]
        return []
