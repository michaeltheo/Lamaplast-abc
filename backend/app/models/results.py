from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Unicode,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import RUN_STATUSES, sql_in
from .mixins import UtcDateTime, surrogate_pk

Money = Numeric(16, 6)


class CostRun(Base):
    __tablename__ = "tbl_CostRuns"
    __table_args__ = (
        CheckConstraint(sql_in("Status", RUN_STATUSES), name="status"),
        Index("IX_tbl_CostRuns_scenario_started", "Scenario_ID", "Started_At"),
    )

    Cost_Run_ID: Mapped[int] = surrogate_pk()
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"))
    Started_At: Mapped[datetime] = mapped_column(UtcDateTime, server_default=func.sysutcdatetime())
    Finished_At: Mapped[datetime | None] = mapped_column(UtcDateTime)
    Status: Mapped[str] = mapped_column(String(10), server_default="RUNNING")
    Run_By: Mapped[str | None] = mapped_column(String(50))
    Engine_Version: Mapped[str | None] = mapped_column(String(20))
    Message: Mapped[str | None] = mapped_column(Unicode(1000))      

    activity_rates: Mapped[list["ActivityRateResult"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    item_costs: Mapped[list["CostResult"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class ActivityRateResult(Base):
    __tablename__ = "tbl_ActivityRateResults"

    Cost_Run_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostRuns.Cost_Run_ID", ondelete="CASCADE"), primary_key=True)
    Activity_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Activities.Activity_ID"), primary_key=True)
    Activity_Cost_EUR: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    Driver_Quantity: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))
    Rate_EUR: Mapped[Decimal | None] = mapped_column(Money)
    Unused_Capacity_EUR: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))


class CostResult(Base):
    __tablename__ = "tbl_CostResults"

    Cost_Run_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostRuns.Cost_Run_ID", ondelete="CASCADE"), primary_key=True)
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), primary_key=True, index=True)
    Material_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Regrind_Credit_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Machine_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Labor_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Setup_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    QC_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Mould_Depr_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Assembly_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Components_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")   
    Overhead_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Scrap_EUR: Mapped[Decimal] = mapped_column(Money, server_default="0")
    Total_Unit_Cost_EUR: Mapped[Decimal] = mapped_column(Money)
    Sales_Price_EUR: Mapped[Decimal | None] = mapped_column(Money)
    Margin_Pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    Warnings: Mapped[str | None] = mapped_column(Unicode(500))   
