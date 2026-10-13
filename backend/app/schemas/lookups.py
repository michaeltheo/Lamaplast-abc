from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LookupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ItemCodeRuleOut(LookupOut):
    Prefix: str
    Description: str
    Item_Type: str
    Material_Source: str
    Zero_Cost: bool
    BOM_Role: str
    ABC_Component_Type: str | None
    Is_Regrind_Source: bool
    Regrind_Value_Override: Decimal | None
    Notes: str | None


class BaseMaterialOut(LookupOut):
    Material_Code: str
    Material_Name: str
    Material_Family: str
    Is_Recyclable: bool
    Default_Regrind_Recovery: Decimal | None
    Default_Regrind_Value: Decimal | None
    Is_Active: bool
    Notes: str | None


class BSSGOut(LookupOut):
    BSSG_Code: str
    BSSG_Name: str
    Sort_order: int | None
    Is_Active: bool


class CommercialPillarOut(LookupOut):
    Pillar_Code: str
    Pillar_Name: str
    BSSG_Code: str
    Sort_order: int | None
    Is_Active: bool


class ProductGroupOut(LookupOut):
    Group_Code: str
    Group_Name: str
    Pillar_Code: str
    Sort_Order: int | None
    Is_Active: bool


class MachineCategoryOut(LookupOut):
    Category_Code: str
    Category_Name: str
    Machine_Group: str
    Clamp_Force_Min_tn: int | None
    Clamp_Force_Max_tn: int | None
    Notes: str | None


class GlobalDefaultOut(LookupOut):
    Parameter: str
    Value: Decimal
    Unit: str | None
    Description: str | None
