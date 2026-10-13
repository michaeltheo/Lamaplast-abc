from decimal import Decimal
from typing import Annotated

from app.schemas.common import AuditedOut, Money, NotesText, PatchModel
from pydantic import BaseModel, Field

# Όρια όπως τα CHECK της βάσης: κόστος >= 0, απασχόληση έως 1.2 (υπερωρίες)
Hours = Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=2)]
Utilization = Annotated[Decimal, Field(ge=0, le=Decimal("1.2"), max_digits=5, decimal_places=4)]


class LaborCreate(BaseModel):
    Employee_Code: str = Field(min_length=1, max_length=15)
    Employee_Name: str = Field(min_length=1, max_length=80)
    Labor_Category: str = Field(min_length=1, max_length=30)
    CC_ID: int
    Resource_ID: int | None = None
    Annual_Cost_EUR: Money
    Actual_Hours_Year: Hours | None = None
    Max_Hours_Year: Decimal = Field(default=Decimal(1776), gt=0, max_digits=8, decimal_places=2)
    Utilization_Rate: Utilization | None = None
    Notes: NotesText | None = None


class LaborUpdate(PatchModel):
    required_fields = frozenset({"Employee_Code", "Employee_Name", "Labor_Category", "CC_ID",
                                 "Annual_Cost_EUR", "Max_Hours_Year"})

    Employee_Code: str | None = Field(default=None, min_length=1, max_length=15)
    Employee_Name: str | None = Field(default=None, min_length=1, max_length=80)
    Labor_Category: str | None = Field(default=None, min_length=1, max_length=30)
    CC_ID: int | None = None
    Resource_ID: int | None = None
    Annual_Cost_EUR: Money | None = None
    Actual_Hours_Year: Hours | None = None
    Max_Hours_Year: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    Utilization_Rate: Utilization | None = None
    Notes: NotesText | None = None


class LaborOut(AuditedOut):
    Employee_ID: int
    Employee_Code: str
    Employee_Name: str | None            # GDPR: null για όποιον δεν είναι ADMIN/EXPERT
    Labor_Category: str
    CC_ID: int
    Resource_ID: int | None
    Annual_Cost_EUR: Decimal
    Actual_Hours_Year: Decimal | None
    Max_Hours_Year: Decimal
    Utilization_Rate: Decimal | None
    Nominal_Rate_EUR_h: Decimal | None   # υπολογίζεται από τη βάση
    Is_Active: bool
    Notes: str | None
