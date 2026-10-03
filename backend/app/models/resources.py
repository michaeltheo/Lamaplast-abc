from decimal import Decimal

from sqlalchemy import CheckConstraint, Computed, ForeignKey, Numeric, SmallInteger, String, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import RESOURCE_TYPES, sql_in
from .mixins import AuditMixin, flag, surrogate_pk


# Resources Table (tbl_Resources)
class Resource(AuditMixin, Base):
    __tablename__ = "tbl_Resources"
    __table_args__ = (CheckConstraint(sql_in("Resource_Type", RESOURCE_TYPES), name="resource_type"),)

    Resource_ID: Mapped[int] = surrogate_pk()
    Resource_Code: Mapped[str] = mapped_column(String(20), unique=True)      # RES-INJ-LAB
    Resource_Name: Mapped[str] = mapped_column(Unicode(80))
    CC_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostCenters.CC_ID"), index=True)
    Resource_Type: Mapped[str] = mapped_column(String(12))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    activity_shares: Mapped[list["ResourceActivity"]] = relationship(back_populates="resource")


# Resource Activity Table (tbl_ResourceActivities)
class ResourceActivity(AuditMixin, Base):
    __tablename__ = "tbl_ResourceActivities"
    __table_args__ = (CheckConstraint("Share_Pct > 0 AND Share_Pct <= 1", name="share"),)

    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"), primary_key=True)
    Resource_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Resources.Resource_ID"), primary_key=True)
    Activity_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Activities.Activity_ID"), primary_key=True)
    Share_Pct: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    Allocation_Basis: Mapped[str | None] = mapped_column(Unicode(80))      
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    resource: Mapped[Resource] = relationship(back_populates="activity_shares")


        
# Buildings Table (tbl_Buildings)
class Building(AuditMixin, Base):
    __tablename__ = "tbl_Buildings"
    __table_args__ = (
        UniqueConstraint("Building_Code", "Zone_Name"),
        CheckConstraint("Cost_Basis IN ('m2','m3')", name="cost_basis"),
        CheckConstraint("Utilization_Pct IS NULL OR Utilization_Pct BETWEEN 0 AND 1", name="utilization"),
    )

    Building_ID: Mapped[int] = surrogate_pk()
    Building_Code: Mapped[str] = mapped_column(Unicode(15))
    Zone_Name: Mapped[str | None] = mapped_column(Unicode(40))
    Ownership: Mapped[str] = mapped_column(Unicode(15), server_default="ΙΔΙΟΚΤΗΤΟ")
    Floor_Level: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    Area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    Height_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    Utilization_Pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Nominal_Volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), Computed("CAST(Area_m2 * Height_m AS NUMERIC(14, 2))", persisted=True))
    Useful_Volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), Computed("CAST(Area_m2 * Height_m * Utilization_Pct AS NUMERIC(14, 2))", persisted=True))
    Cost_Basis: Mapped[str] = mapped_column(String(3), server_default="m2")
    CC_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostCenters.CC_ID"), index=True)
    Resource_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Resources.Resource_ID"), index=True)
    Depreciation_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")     
    Equipment_Depr_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    IT_Depr_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    Total_Cost_EUR: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), Computed("CAST(Depreciation_EUR + Equipment_Depr_EUR + IT_Depr_EUR AS NUMERIC(14, 2))", persisted=True))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))


# Machines Table (tbl_Machines)
class Machine(AuditMixin, Base):
    __tablename__ = "tbl_Machines"
    __table_args__ = (
        CheckConstraint("Hours_Per_Day > 0 AND Hours_Per_Day <= 24", name="hours"),
        CheckConstraint("Days_Per_Year > 0 AND Days_Per_Year <= 366", name="days"),
        CheckConstraint("Downtime_Pct IS NULL OR Downtime_Pct BETWEEN 0 AND 1", name="downtime"),
    )

    Machine_ID: Mapped[int] = surrogate_pk()
    Machine_Code: Mapped[str] = mapped_column(String(15), unique=True)       
    Description: Mapped[str] = mapped_column(Unicode(80))
    Category_Code: Mapped[str] = mapped_column(ForeignKey("tbl_MachineCategories.Category_Code"), index=True)
    CC_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostCenters.CC_ID"), index=True)
    Resource_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Resources.Resource_ID"), index=True)
    Building_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Buildings.Building_ID"))
    Power_KW_Motor: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    Power_KW_Thermal: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    Power_KW_Measured: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))   
    Clamp_Force_tn: Mapped[int | None] = mapped_column(SmallInteger)
    Year_Built: Mapped[int | None] = mapped_column(SmallInteger)
    Country_Origin: Mapped[str | None] = mapped_column(Unicode(30))
    Acquisition_Cost_EUR: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    Residual_Value_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    Useful_Life_Years: Mapped[int | None] = mapped_column(SmallInteger)
    Maintenance_Cost_Year_EUR: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))   
    Hours_Per_Day: Mapped[Decimal] = mapped_column(Numeric(4, 1), server_default="16")
    Days_Per_Year: Mapped[int] = mapped_column(SmallInteger, server_default="222")
    Downtime_Pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))                
    Annual_Hours: Mapped[Decimal] = mapped_column(Numeric(10, 1), Computed("CAST(Hours_Per_Day * Days_Per_Year AS NUMERIC(10, 1))", persisted=True))
    Depreciation_Per_Hour: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        Computed("CAST((Acquisition_Cost_EUR - Residual_Value_EUR) / NULLIF(Useful_Life_Years * Hours_Per_Day * Days_Per_Year, 0) AS NUMERIC(12, 6))",
                 persisted=True))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))




# Labor resources (employees or categories of employees)
class LaborResource(AuditMixin, Base):
    __tablename__ = "tbl_LaborResources"
    __table_args__ = (
        CheckConstraint("Annual_Cost_EUR >= 0", name="cost"),
        CheckConstraint("Utilization_Rate IS NULL OR Utilization_Rate BETWEEN 0 AND 1.2", name="utilization"),
    )

    Employee_ID: Mapped[int] = surrogate_pk()
    Employee_Code: Mapped[str] = mapped_column(String(15), unique=True)
    Employee_Name: Mapped[str] = mapped_column(Unicode(80))
    Labor_Category: Mapped[str] = mapped_column(Unicode(30))                  
    CC_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostCenters.CC_ID"), index=True)
    Resource_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Resources.Resource_ID"), index=True)
    Annual_Cost_EUR: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    Actual_Hours_Year: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    Max_Hours_Year: Mapped[Decimal] = mapped_column(Numeric(8, 2), server_default="1776")
    Utilization_Rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Nominal_Rate_EUR_h: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        Computed("CAST(Annual_Cost_EUR / NULLIF(COALESCE(Actual_Hours_Year, Max_Hours_Year), 0) AS NUMERIC(10, 4))", persisted=True))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))
