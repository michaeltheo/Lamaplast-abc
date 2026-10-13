from decimal import Decimal
from typing import Annotated

from app.schemas.common import AuditedOut, Money, NotesText, PatchModel, Pct
from pydantic import BaseModel, Field

Power = Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=2)]


class MachineCreate(BaseModel):
    Machine_Code: str = Field(min_length=1, max_length=15)
    Description: str = Field(min_length=1, max_length=80)
    Category_Code: str = Field(min_length=1, max_length=5)
    CC_ID: int
    Resource_ID: int | None = None
    Building_ID: int | None = None
    Power_KW_Motor: Power | None = None
    Power_KW_Thermal: Power | None = None
    Power_KW_Measured: Power | None = None
    Clamp_Force_tn: int | None = Field(default=None, ge=0, le=32767)
    Year_Built: int | None = Field(default=None, ge=1900, le=2100)
    Country_Origin: str | None = Field(default=None, max_length=30)
    Acquisition_Cost_EUR: Money | None = None
    Residual_Value_EUR: Money = Decimal(0)
    Useful_Life_Years: int | None = Field(default=None, gt=0, le=100)
    Maintenance_Cost_Year_EUR: Money | None = None
    Hours_Per_Day: Decimal = Field(default=Decimal(16), gt=0, le=24, max_digits=4, decimal_places=1)
    Days_Per_Year: int = Field(default=222, gt=0, le=366)
    Downtime_Pct: Pct | None = None
    Notes: NotesText | None = None


class MachineUpdate(PatchModel):
    required_fields = frozenset({"Machine_Code", "Description", "Category_Code", "CC_ID",
                                 "Residual_Value_EUR", "Hours_Per_Day", "Days_Per_Year"})

    Machine_Code: str | None = Field(default=None, min_length=1, max_length=15)
    Description: str | None = Field(default=None, min_length=1, max_length=80)
    Category_Code: str | None = Field(default=None, min_length=1, max_length=5)
    CC_ID: int | None = None
    Resource_ID: int | None = None
    Building_ID: int | None = None
    Power_KW_Motor: Power | None = None
    Power_KW_Thermal: Power | None = None
    Power_KW_Measured: Power | None = None
    Clamp_Force_tn: int | None = Field(default=None, ge=0, le=32767)
    Year_Built: int | None = Field(default=None, ge=1900, le=2100)
    Country_Origin: str | None = Field(default=None, max_length=30)
    Acquisition_Cost_EUR: Money | None = None
    Residual_Value_EUR: Money | None = None
    Useful_Life_Years: int | None = Field(default=None, gt=0, le=100)
    Maintenance_Cost_Year_EUR: Money | None = None
    Hours_Per_Day: Decimal | None = Field(default=None, gt=0, le=24, max_digits=4, decimal_places=1)
    Days_Per_Year: int | None = Field(default=None, gt=0, le=366)
    Downtime_Pct: Pct | None = None
    Notes: NotesText | None = None


class MachineOut(AuditedOut):
    Machine_ID: int
    Machine_Code: str
    Description: str
    Category_Code: str
    CC_ID: int
    Resource_ID: int | None
    Building_ID: int | None
    Power_KW_Motor: Decimal | None
    Power_KW_Thermal: Decimal | None
    Power_KW_Measured: Decimal | None
    Clamp_Force_tn: int | None
    Year_Built: int | None
    Country_Origin: str | None
    Acquisition_Cost_EUR: Decimal | None
    Residual_Value_EUR: Decimal
    Useful_Life_Years: int | None
    Maintenance_Cost_Year_EUR: Decimal | None
    Hours_Per_Day: Decimal
    Days_Per_Year: int
    Downtime_Pct: Decimal | None
    Annual_Hours: Decimal                    # υπολογίζεται από τη βάση
    Depreciation_Per_Hour: Decimal | None    # υπολογίζεται από τη βάση
    Is_Active: bool
    Notes: str | None
