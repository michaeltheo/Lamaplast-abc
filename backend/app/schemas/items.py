from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import OrmOut

# --- Logistics units ---


class LogisticsUnitIn(BaseModel):
    LU_Level: int = Field(ge=1, le=3)
    Description: str | None = Field(default=None, max_length=60)
    Base_Units_Per_LU: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    Gross_Weight_kg: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)
    Length_m: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=3)
    Width_m: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=3)
    Height_m: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=3)
    Is_Informational: bool = False


class LogisticsUnitOut(OrmOut):
    LU_ID: int
    Item_ID: int
    LU_Level: int
    Description: str | None
    Base_Units_Per_LU: Decimal
    Gross_Weight_kg: Decimal | None
    Length_m: Decimal | None
    Width_m: Decimal | None
    Height_m: Decimal | None
    Volume_m3: Decimal | None  # υπολογίζεται από τη βάση
    Is_Informational: bool


# --- Items ---


class ItemCreate(BaseModel):
    Item_Code: str = Field(min_length=1, max_length=20)
    Item_Name: str = Field(min_length=1, max_length=100)
    Item_Category_Prefix: str = Field(min_length=1, max_length=5)
    BSSG_Code: str | None = Field(default=None, max_length=2)
    Pillar_Code: str | None = Field(default=None, max_length=10)
    Group_Code: str | None = Field(default=None, max_length=15)
    Base_Material_Code: str | None = Field(default=None, max_length=5)
    Customer_ID: int | None = None
    UoM: str = Field(default="τεμ.", min_length=1, max_length=10)
    Weight_kg: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=5)
    Density_g_cm3: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=4)
    Fason_Base_Item_ID: int | None = None
    Regrind_Value_Override: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    Is_Purchased: bool = False
    Is_Produced: bool = False
    ERP_Code: str | None = Field(default=None, max_length=30)
    Notes: str | None = Field(default=None, max_length=200)


class ItemUpdate(BaseModel):
    """Όλα προαιρετικά: αλλάζουν μόνο όσα πεδία στάλθηκαν (model_dump(exclude_unset=True))."""
    Item_Code: str | None = Field(default=None, min_length=1, max_length=20)
    Item_Name: str | None = Field(default=None, min_length=1, max_length=100)
    Item_Category_Prefix: str | None = Field(default=None, min_length=1, max_length=5)
    BSSG_Code: str | None = Field(default=None, max_length=2)
    Pillar_Code: str | None = Field(default=None, max_length=10)
    Group_Code: str | None = Field(default=None, max_length=15)
    Base_Material_Code: str | None = Field(default=None, max_length=5)
    Customer_ID: int | None = None
    UoM: str | None = Field(default=None, min_length=1, max_length=10)
    Weight_kg: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=5)
    Density_g_cm3: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=4)
    Fason_Base_Item_ID: int | None = None
    Regrind_Value_Override: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    Is_Purchased: bool | None = None
    Is_Produced: bool | None = None
    ERP_Code: str | None = Field(default=None, max_length=30)
    Notes: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def required_columns_cannot_be_cleared(self) -> Self:
        # null σε προαιρετική στήλη = «σβήσε την τιμή»· σε υποχρεωτική στήλη δεν έχει νόημα
        required = {"Item_Code", "Item_Name", "Item_Category_Prefix", "UoM", "Is_Purchased", "Is_Produced"}
        for field in sorted(self.model_fields_set & required):
            if getattr(self, field) is None:
                raise ValueError(f"Το πεδίο {field} δεν μπορεί να είναι κενό")
        return self


class ItemListOut(OrmOut):
    Item_ID: int
    Item_Code: str
    Item_Name: str
    Item_Category_Prefix: str
    BSSG_Code: str | None
    Pillar_Code: str | None
    Group_Code: str | None
    Customer_ID: int | None
    UoM: str
    Is_Purchased: bool
    Is_Produced: bool
    Is_Active: bool


class ItemOut(ItemListOut):
    Base_Material_Code: str | None
    Weight_kg: Decimal | None
    Density_g_cm3: Decimal | None
    Fason_Base_Item_ID: int | None
    Regrind_Value_Override: Decimal | None
    ERP_Code: str | None
    Notes: str | None
    Created_At: datetime
    Created_By: str | None
    Updated_At: datetime | None
    Updated_By: str | None
    logistics_units: list[LogisticsUnitOut]

    @field_validator("logistics_units", mode="before")
    @classmethod
    def by_level(cls, units):
        return sorted(units, key=lambda lu: lu.LU_Level)
