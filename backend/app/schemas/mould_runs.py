from decimal import Decimal
from typing import Annotated, Literal

from app.models.enums import MIX_MATERIAL_TYPES, OPERATOR_LOADS
from app.schemas.common import AuditedOut, NotesText, OrmOut, Pct
from pydantic import BaseModel, Field, field_validator

Grams = Annotated[Decimal, Field(max_digits=10, decimal_places=3)]
Minutes = Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=1)]


class MouldRunOutputIn(BaseModel):
    Item_ID: int
    Pieces_Per_Cycle: int = Field(ge=1, le=32767)
    Net_Part_Weight_g: Grams = Field(gt=0)
    Cost_Share_Pct: Decimal | None = Field(default=None, ge=0, le=1, max_digits=7, decimal_places=6)
    Is_Default: bool = True


class MouldRunMaterialIn(BaseModel):
    Material_Item_ID: int
    Material_Type: Literal[*MIX_MATERIAL_TYPES] = "BASE_RESIN"
    Mix_Pct: Decimal = Field(gt=0, le=1, max_digits=7, decimal_places=5)      # 0.98 = 98%
    Is_Regrind_Source: bool = False
    Regrind_Value_Override: Pct | None = None
    Sequence: int = Field(default=10, ge=0, le=32767)


class MouldRunIn(BaseModel):
    """Το run μαζί με τα παιδιά του. Ίδιο σχήμα για POST και PUT: το PUT αντικαθιστά τα πάντα."""
    MouldRun_Code: str = Field(min_length=1, max_length=20)
    Mould_ID: int
    Machine_Category: str = Field(min_length=1, max_length=5)
    Cycles_Per_Hour: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    Operator_Load_Factor: Decimal = Decimal(1)
    Sprue_Runner_Total_g: Grams = Field(default=Decimal(0), ge=0)
    Scrap_Pct: Pct = Decimal("0.041")
    Regrind_Recovery_Override: Pct | None = None
    Max_Regrind_In_Mix_Pct: Pct | None = None
    Setup_Min: Minutes = Decimal(41)
    Setdown_Min: Minutes = Decimal(22)
    Avg_Batch_Qty: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=0)
    QC_Hours_Per_Batch: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)
    Notes: NotesText | None = None
    outputs: list[MouldRunOutputIn] = Field(min_length=1)
    materials: list[MouldRunMaterialIn] = Field(min_length=1)

    @field_validator("Operator_Load_Factor")
    @classmethod
    def allowed_operator_load(cls, value: Decimal) -> Decimal:
        if value not in {Decimal(load) for load in OPERATOR_LOADS}:
            raise ValueError(f"Επιτρεπτές τιμές: {', '.join(OPERATOR_LOADS)}")
        return value


class MouldRunOutputOut(OrmOut):
    MouldRun_ID: int
    Item_ID: int
    Pieces_Per_Cycle: int
    Net_Part_Weight_g: Decimal
    Cost_Share_Pct: Decimal | None
    Is_Default: bool


class MouldRunMaterialOut(OrmOut):
    MouldRun_ID: int
    Material_Item_ID: int
    Material_Type: str
    Mix_Pct: Decimal
    Is_Regrind_Source: bool
    Regrind_Value_Override: Decimal | None
    Sequence: int


class MouldRunOut(AuditedOut):
    MouldRun_ID: int
    MouldRun_Code: str
    Mould_ID: int
    Machine_Category: str
    Cycles_Per_Hour: Decimal
    Sec_Per_Cycle: Decimal                # υπολογίζεται από τη βάση
    Operator_Load_Factor: Decimal
    Sprue_Runner_Total_g: Decimal
    Scrap_Pct: Decimal
    Regrind_Recovery_Override: Decimal | None
    Max_Regrind_In_Mix_Pct: Decimal | None
    Setup_Min: Decimal
    Setdown_Min: Decimal
    Avg_Batch_Qty: Decimal | None
    QC_Hours_Per_Batch: Decimal | None
    Is_Active: bool
    Notes: str | None
    outputs: list[MouldRunOutputOut]
    materials: list[MouldRunMaterialOut]

    @field_validator("outputs", mode="before")
    @classmethod
    def outputs_by_item(cls, outputs):
        return sorted(outputs, key=lambda o: o.Item_ID)

    @field_validator("materials", mode="before")
    @classmethod
    def materials_by_sequence(cls, materials):
        return sorted(materials, key=lambda m: (m.Sequence, m.Material_Item_ID))
