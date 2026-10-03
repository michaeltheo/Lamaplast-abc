from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    ASSEMBLY_TYPES,
    MIX_MATERIAL_TYPES,
    MOULD_OWNERS,
    MOULD_TYPES,
    OPERATOR_LOADS,
    sql_in,
)
from .mixins import AuditMixin, flag, surrogate_pk


class Mould(AuditMixin, Base):
    __tablename__ = "tbl_Moulds"
    __table_args__ = (
        CheckConstraint(sql_in("Mould_Owner", MOULD_OWNERS), name="owner"),
        CheckConstraint(sql_in("Mould_Type", MOULD_TYPES), name="mould_type"),
        CheckConstraint("QC_Factor BETWEEN 1 AND 3", name="qc_factor"),
        CheckConstraint("Cavities >= 1", name="cavities"),
        CheckConstraint("Residual_Value_EUR <= Acquisition_Cost_EUR", name="residual"),
    )

    Mould_ID: Mapped[int] = surrogate_pk()
    Mould_Code: Mapped[str] = mapped_column(String(20), unique=True)        
    Mould_Name: Mapped[str] = mapped_column(Unicode(100))
    Item_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Items.Item_ID"))   
    Mould_Owner: Mapped[str] = mapped_column(String(10), server_default="LAMAPLAST")
    Customer_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Customers.Customer_ID"))
    Mould_Type: Mapped[str] = mapped_column(String(12), server_default="SINGLE")
    Cavities: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    Default_Machine_Category: Mapped[str | None] = mapped_column(ForeignKey("tbl_MachineCategories.Category_Code"))
    Acquisition_Cost_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    Residual_Value_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    Depreciable_Value_EUR: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), Computed("Acquisition_Cost_EUR - Residual_Value_EUR", persisted=True))
    Life_Cycles: Mapped[int | None] = mapped_column(Integer)
    Current_Cycles: Mapped[int] = mapped_column(Integer, server_default="0")
    Wear_Pct: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4), Computed("CAST(Current_Cycles AS DECIMAL(14,4)) / NULLIF(Life_Cycles, 0)", persisted=True))
    Depreciation_Per_Cycle: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), Computed("(Acquisition_Cost_EUR - Residual_Value_EUR) / NULLIF(Life_Cycles, 0)", persisted=True))
    QC_Factor: Mapped[int] = mapped_column(SmallInteger, server_default="2")   
    Technicians: Mapped[int | None] = mapped_column(SmallInteger)
    Year_Constructed: Mapped[int | None] = mapped_column(SmallInteger)
    Replacement_Estimate: Mapped[date | None] = mapped_column(Date)
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    runs: Mapped[list["MouldRun"]] = relationship(back_populates="mould")

#   Mould Run 
class MouldRun(AuditMixin, Base):
    __tablename__ = "tbl_MouldRuns"
    __table_args__ = (
        UniqueConstraint("Mould_ID", "Machine_Category"),
        CheckConstraint("Cycles_Per_Hour > 0", name="cycles"),
        CheckConstraint(sql_in("Operator_Load_Factor", OPERATOR_LOADS, numeric=True), name="operator_load"),
        CheckConstraint("Scrap_Pct BETWEEN 0 AND 1", name="scrap"),
        CheckConstraint("Avg_Batch_Qty IS NULL OR Avg_Batch_Qty > 0", name="batch"),
    )

    MouldRun_ID: Mapped[int] = surrogate_pk()
    MouldRun_Code: Mapped[str] = mapped_column(String(20), unique=True)      # MR-001
    Mould_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Moulds.Mould_ID"), index=True)
    Machine_Category: Mapped[str] = mapped_column(ForeignKey("tbl_MachineCategories.Category_Code"))
    Cycles_Per_Hour: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    Sec_Per_Cycle: Mapped[Decimal] = mapped_column(Numeric(10, 3), Computed("3600.0 / Cycles_Per_Hour", persisted=True))
    Operator_Load_Factor: Mapped[Decimal] = mapped_column(Numeric(4, 2), server_default="1")
    Sprue_Runner_Total_g: Mapped[Decimal] = mapped_column(Numeric(10, 3), server_default="0")   
    Scrap_Pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), server_default="0.041")
    Regrind_Recovery_Override: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))            
    Max_Regrind_In_Mix_Pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Setup_Min: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="41")
    Setdown_Min: Mapped[Decimal] = mapped_column(Numeric(6, 1), server_default="22")
    Avg_Batch_Qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 0))                      
    QC_Hours_Per_Batch: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))              
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    mould: Mapped[Mould] = relationship(back_populates="runs")
    outputs: Mapped[list["MouldRunOutput"]] = relationship(back_populates="mould_run", cascade="all, delete-orphan")
    materials: Mapped[list["MouldRunMaterial"]] = relationship(back_populates="mould_run", cascade="all, delete-orphan")


# Mould Run Output
class MouldRunOutput(AuditMixin, Base):
    __tablename__ = "tbl_MouldRunOutputs"
    __table_args__ = (
        CheckConstraint("Pieces_Per_Cycle >= 1", name="pieces"),
        CheckConstraint("Net_Part_Weight_g > 0", name="weight"),
        CheckConstraint("Cost_Share_Pct IS NULL OR Cost_Share_Pct BETWEEN 0 AND 1", name="share"),
    )

    MouldRun_ID: Mapped[int] = mapped_column(ForeignKey("tbl_MouldRuns.MouldRun_ID", ondelete="CASCADE"), primary_key=True)
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), primary_key=True, index=True)
    Pieces_Per_Cycle: Mapped[int] = mapped_column(SmallInteger)
    Net_Part_Weight_g: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    Cost_Share_Pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))     
    Is_Default: Mapped[bool] = flag(True)

    mould_run: Mapped[MouldRun] = relationship(back_populates="outputs")

class MouldRunMaterial(AuditMixin, Base):
    __tablename__ = "tbl_MouldRunMaterials"
    __table_args__ = (
        CheckConstraint(sql_in("Material_Type", MIX_MATERIAL_TYPES), name="material_type"),
        CheckConstraint("Mix_Pct > 0 AND Mix_Pct <= 1", name="mix"),
    )

    MouldRun_ID: Mapped[int] = mapped_column(ForeignKey("tbl_MouldRuns.MouldRun_ID", ondelete="CASCADE"), primary_key=True)
    Material_Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), primary_key=True, index=True)
    Material_Type: Mapped[str] = mapped_column(String(12), server_default="BASE_RESIN")
    Mix_Pct: Mapped[Decimal] = mapped_column(Numeric(7, 5))
    Is_Regrind_Source: Mapped[bool] = flag(False)
    Regrind_Value_Override: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Sequence: Mapped[int] = mapped_column(SmallInteger, server_default="10")

    mould_run: Mapped[MouldRun] = relationship(back_populates="materials")


class AssemblyOp(AuditMixin, Base):
    __tablename__ = "tbl_AssemblyOps"
    __table_args__ = (
        CheckConstraint(sql_in("Operation_Type", ASSEMBLY_TYPES), name="operation_type"),
        CheckConstraint("Units_Per_Hour > 0", name="units"),
        CheckConstraint("Workers_Per_Cell > 0", name="workers"),
    )

    AssemblyOp_ID: Mapped[int] = surrogate_pk()
    AssemblyOp_Code: Mapped[str] = mapped_column(String(20), unique=True)    
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), index=True)
    Operation_Name: Mapped[str] = mapped_column(Unicode(100))
    Activity_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Activities.Activity_ID"))
    Operation_Type: Mapped[str] = mapped_column(String(6), server_default="OWN")
    Workers_Per_Cell: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="1")
    Units_Per_Hour: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    Sec_Per_Unit: Mapped[Decimal] = mapped_column(Numeric(10, 3), Computed("3600.0 / Units_Per_Hour", persisted=True))
    Labor_Hrs_Per_Unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), Computed("Workers_Per_Cell / Units_Per_Hour", persisted=True))
    Sequence: Mapped[int] = mapped_column(SmallInteger, server_default="10")
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))
