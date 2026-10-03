from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins import AuditMixin, flag, surrogate_pk


# Customers Table (tbl_Customers)
class Customer(AuditMixin, Base):
    __tablename__ = "tbl_Customers"

    Customer_ID: Mapped[int] = surrogate_pk()
    Customer_Code: Mapped[str] = mapped_column(String(10), unique=True)  
    Customer_Name: Mapped[str] = mapped_column(Unicode(100))
    Is_Internal: Mapped[bool] = flag(False)
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))


# Items Table (tbl_Items)
class Item(AuditMixin, Base):
    __tablename__ = "tbl_Items"
    __table_args__ = (
        CheckConstraint("Weight_kg IS NULL OR Weight_kg >= 0", name="weight"),
        CheckConstraint("Fason_Base_Item_ID IS NULL OR Fason_Base_Item_ID <> Item_ID", name="fason_not_self"),
    )

    Item_ID: Mapped[int] = surrogate_pk()
    Item_Code: Mapped[str] = mapped_column(String(20), unique=True)
    Item_Name: Mapped[str] = mapped_column(Unicode(100))
    Item_Category_Prefix: Mapped[str] = mapped_column(ForeignKey("tbl_ItemCodeRules.Prefix"), index=True)
    BSSG_Code: Mapped[str | None] = mapped_column(ForeignKey("tbl_BSSG.BSSG_Code"), index=True)
    Pillar_Code: Mapped[str | None] = mapped_column(ForeignKey("tbl_CommercialPillars.Pillar_Code"))
    Group_Code: Mapped[str | None] = mapped_column(ForeignKey("tbl_ProductGroups.Group_Code"), index=True)
    Base_Material_Code: Mapped[str | None] = mapped_column(ForeignKey("tbl_BaseMaterials.Material_Code"))
    Customer_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Customers.Customer_ID"), index=True)  # null means it's ours 
    UoM: Mapped[str] = mapped_column(Unicode(10), server_default="τεμ.")
    Weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 5))
    Density_g_cm3: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    Fason_Base_Item_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Items.Item_ID"))   
    Regrind_Value_Override: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))               
    Is_Purchased: Mapped[bool] = flag(False)
    Is_Produced: Mapped[bool] = flag(False)
    Is_Active: Mapped[bool] = flag(True)
    ERP_Code: Mapped[str | None] = mapped_column(String(30), index=True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    logistics_units: Mapped[list["LogisticsUnit"]] = relationship(back_populates="item", cascade="all, delete-orphan")


# Logistics Units Table (tbl_LogisticsUnits)
class LogisticsUnit(AuditMixin, Base):
    __tablename__ = "tbl_LogisticsUnits"
    __table_args__ = (
        UniqueConstraint("Item_ID", "LU_Level"),
        CheckConstraint("LU_Level BETWEEN 1 AND 3", name="lu_level"),
    )

    LU_ID: Mapped[int] = surrogate_pk()
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID", ondelete="CASCADE"))
    LU_Level: Mapped[int] = mapped_column(SmallInteger)
    Description: Mapped[str | None] = mapped_column(Unicode(60))           
    Base_Units_Per_LU: Mapped[Decimal] = mapped_column(Numeric(12, 3))     
    Gross_Weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    Length_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    Width_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    Height_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    Volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), Computed("CAST(Length_m * Width_m * Height_m AS NUMERIC(12, 6))", persisted=True))
    Is_Informational: Mapped[bool] = flag(False)   

    item: Mapped[Item] = relationship(back_populates="logistics_units")
