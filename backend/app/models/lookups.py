
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Unicode,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    BOM_ROLES,
    ITEM_TYPES,
    MACHINE_GROUPS,
    MATERIAL_FAMILIES,
    MATERIAL_SOURCES,
    sql_in,
)
from .mixins import AuditMixin, flag


class GlobeDefault(AuditMixin, Base):
    __tablename__ = "tbl_GlobalDefaults"

    Parameter: Mapped[str]=mapped_column(String(50),primary_key=True)
    Value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    Unit: Mapped[str | None] = mapped_column(Unicode(20))
    Description: Mapped[str | None] = mapped_column(Unicode(200))


# Item code rules define the meaning of item code prefixes and their associated attributes.
class ItemCodeRule(AuditMixin, Base):
    __tablename__ = "tbl_ItemCodeRules"
    __table_args__ = (
        CheckConstraint(sql_in("Item_Type", ITEM_TYPES), name="item_type"),
        CheckConstraint(sql_in("Material_Source", MATERIAL_SOURCES), name="material_source"),
        CheckConstraint(sql_in("BOM_Role", BOM_ROLES), name="bom_role"),
    )

    Prefix: Mapped[str] = mapped_column(String(5), primary_key=True)
    Description: Mapped[str] = mapped_column(Unicode(60))
    Item_Type: Mapped[str] = mapped_column(String(20))
    Material_Source: Mapped[str] = mapped_column(String(10), server_default="LAMAPLAST")
    Zero_Cost: Mapped[bool] = flag(False)         
    BOM_Role: Mapped[str] = mapped_column(String(10))
    ABC_Component_Type: Mapped[str | None] = mapped_column(String(20))
    Is_Regrind_Source: Mapped[bool] = flag(False)
    Regrind_Value_Override: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Notes: Mapped[str | None] = mapped_column(Unicode(200))


# Base material lookup table defines the available base materials and their default regrind settings.
class BaseMaterial(AuditMixin, Base):
    __tablename__ = "tbl_BaseMaterial"
    __table_args__ = (
        CheckConstraint(sql_in("Material_Family", MATERIAL_FAMILIES), name="material_family"),
        CheckConstraint("Default_Regrind_Recovery BETWEEN 0 AND 1", name="regrind_recovery"),
        CheckConstraint("Default_Regrind_Value BETWEEN 0 AND 1", name="regrind_value"),
    )

    Material_Code: Mapped[str] = mapped_column(String(5), primary_key=True)
    Material_Name: Mapped[str] = mapped_column(Unicode(40))
    Material_Family: Mapped[str] = mapped_column(String(20))
    Is_Recyclable: Mapped[bool] = flag(False)
    Default_Regrind_Recovery: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Default_Regrind_Value: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

# BSSG lookup table defines the available BSSG entries used in the application.
class BSSG(AuditMixin, Base):
    __tablename__ = "tbl_BSSG"

    BSSG_Coode: Mapped[str] = mapped_column(String(2), primary_key=True)
    BSSG_Name: Mapped[str] = mapped_column(Unicode(40))
    Sort_order: Mapped[int | None] = mapped_column(SmallInteger)
    IsActive: Mapped[bool] = flag(True)
    pillars:Mapped[list["CommercialPillar"]]=relationship(back_populates="bssg")


# Commercial Pillar lookup table defines the available commercial pillars and their association with BSSG entries.
class CommercialPillar(AuditMixin, Base):
    __tablename__ = "tbl_CommercialPillars"

    Pillar_Code: Mapped[str] = mapped_column(String(10), primary_key=True)
    Pillar_Name: Mapped[str] = mapped_column(Unicode(60))
    BSSG_Code: Mapped[str] = mapped_column(ForeignKey("tbl_BSSG.BSSG_Coode"),index=True)
    Sort_order: Mapped[int | None] = mapped_column(SmallInteger)
    IsActive: Mapped[bool] = flag(True)

    bssg: Mapped["BSSG"] = relationship(back_populates="pillars")
    groups: Mapped[list["ProductGroup"]] = relationship(back_populates="pillar")


# Product Group lookup table defines the available product groups and their association with commercial pillars.
class ProductGroup(AuditMixin, Base):
    __tablename__ = "tbl_ProductGroups"

    Group_Code: Mapped[str] = mapped_column(String(15), primary_key=True)
    Group_Name: Mapped[str] = mapped_column(Unicode(80))
    Pillar_Code: Mapped[str] = mapped_column(ForeignKey("tbl_CommercialPillars.Pillar_Code"), index=True)
    Sort_order: Mapped[int | None] = mapped_column(SmallInteger)
    IsActive: Mapped[bool] = flag(True)

    pillar: Mapped["CommercialPillar"] = relationship(back_populates="groups")


class MachineCategories(AuditMixin, Base):
    __tablename__ = "tbl_MachineCategories"

    __table_args__ = (
            CheckConstraint(sql_in("Machine_Group", MACHINE_GROUPS), name="machine_group"),
    )
    

    Category_Code: Mapped[str] = mapped_column(String(5), primary_key=True)
    Category_Name: Mapped[str] = mapped_column(Unicode(40))
    Machine_Group: Mapped[str] = mapped_column(String(10), server_default="INJECTION")
    Clamp_Force_Min_tn: Mapped[int | None] = mapped_column(SmallInteger)
    Clamp_Force_Max_tn: Mapped[int | None] = mapped_column(SmallInteger)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))