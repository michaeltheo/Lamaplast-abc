
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Unicode,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    DATA_SOURCES,
    OVERRIDE_FIELDS,
    OVERRIDE_TARGETS,
    SCENARIO_TYPES,
    sql_in,
)
from .mixins import AuditMixin, UtcDateTime, flag, surrogate_pk


# Scenarios Table (tbl_Scenarios)
class Scenario(AuditMixin, Base):
    __tablename__ = "tbl_Scenarios"
    __table_args__ = (
        CheckConstraint(sql_in("Scenario_Type", SCENARIO_TYPES), name="scenario_type"),
        CheckConstraint("Base_Scenario_ID IS NULL OR Base_Scenario_ID <> Scenario_ID", name="base_not_self"),
        Index("UX_tbl_Scenarios_one_baseline", "Is_Baseline", unique=True, mssql_where=text("Is_Baseline = 1")),
    )

    Scenario_ID: Mapped[int] = surrogate_pk()
    Scenario_Name: Mapped[str] = mapped_column(Unicode(60), unique=True)
    Scenario_Type: Mapped[str] = mapped_column(String(10))
    Base_Scenario_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID"))
    Period_Year: Mapped[int] = mapped_column(SmallInteger)
    Owner_User_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Users.User_ID"), index=True) 
    Is_Locked: Mapped[bool] = flag(False)
    Is_Baseline: Mapped[bool] = flag(False)
    Locked_At: Mapped[datetime | None] = mapped_column(UtcDateTime)
    Locked_By: Mapped[str | None] = mapped_column(String(50))
    Description: Mapped[str | None] = mapped_column(Unicode(200))

    base: Mapped["Scenario | None"] = relationship(remote_side="Scenario.Scenario_ID")



# Scenario Parameters Table (tbl_ScenarioParameters)
class ScenarioParameter(AuditMixin, Base):
    __tablename__ = "tbl_ScenarioParameters"

    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"), primary_key=True)
    Parameter: Mapped[str] = mapped_column(ForeignKey("tbl_GlobalDefault.Parameter"), primary_key=True)
    Value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    Reason: Mapped[str | None] = mapped_column(Unicode(200))


# Scenario Overrides Table (tbl_ScenarioOverrides)
class ScenarioOverride(AuditMixin, Base):
    __tablename__ = "tbl_ScenarioOverrides"
    __table_args__ = (
        CheckConstraint(sql_in("Target_Type", OVERRIDE_TARGETS), name="target_type"),
        CheckConstraint(sql_in("Field_Name", OVERRIDE_FIELDS), name="field_name"),
        UniqueConstraint("Scenario_ID", "Target_Type", "Target_ID", "Field_Name"),
    )

    Override_ID: Mapped[int] = surrogate_pk()
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"))
    Target_Type: Mapped[str] = mapped_column(String(10))
    Target_ID: Mapped[int] = mapped_column(Integer)    
    Field_Name: Mapped[str] = mapped_column(String(40))
    Value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    Reason: Mapped[str | None] = mapped_column(Unicode(200))


# Prices Table (tbl_Prices)
class Price(AuditMixin, Base):
    __tablename__ = "tbl_Prices"
    __table_args__ = (
        UniqueConstraint("Item_ID", "Scenario_ID", "Valid_From"),
        CheckConstraint("Valid_To IS NULL OR Valid_To >= Valid_From", name="valid_range"),
        CheckConstraint("Price_EUR >= 0", name="price_positive"),
        CheckConstraint(sql_in("Source", DATA_SOURCES), name="source"),
    )

    Price_ID: Mapped[int] = surrogate_pk()
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), index=True)
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID"), index=True)
    Valid_From: Mapped[date] = mapped_column(Date)
    Valid_To: Mapped[date | None] = mapped_column(Date)               
    Price_EUR: Mapped[Decimal] = mapped_column(Numeric(14, 5))
    Currency: Mapped[str] = mapped_column(String(3), server_default="EUR")
    FX_Rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default=text("1"))
    Price_Local: Mapped[Decimal | None] = mapped_column(Numeric(14, 5))
    Supplier: Mapped[str | None] = mapped_column(Unicode(100))
    Source: Mapped[str] = mapped_column(String(12), server_default="MANUAL")
    Reason: Mapped[str | None] = mapped_column(Unicode(200))       


# Sales Prices Table (tbl_SalesPrices)
class SalesPrice(AuditMixin, Base):
    __tablename__ = "tbl_SalesPrices"
    __table_args__ = (
        UniqueConstraint("Item_ID", "Customer_ID", "Scenario_ID", "Valid_From"),
        CheckConstraint("Valid_To IS NULL OR Valid_To >= Valid_From", name="valid_range"),
        CheckConstraint("Price_EUR >= 0", name="price_positive"),
        CheckConstraint(sql_in("Source", DATA_SOURCES), name="source"),
    )

    Sales_Price_ID: Mapped[int] = surrogate_pk()
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), index=True)
    Customer_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Customers.Customer_ID"))
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID"), index=True)
    Valid_From: Mapped[date] = mapped_column(Date)
    Valid_To: Mapped[date | None] = mapped_column(Date)
    Price_EUR: Mapped[Decimal] = mapped_column(Numeric(14, 5))
    Source: Mapped[str] = mapped_column(String(12), server_default="MANUAL")
    Reason: Mapped[str | None] = mapped_column(Unicode(200))


# Item Volumes Table (tbl_ItemVolumes)
class ItemVolume(AuditMixin, Base):
    __tablename__ = "tbl_ItemVolumes"
    __table_args__ = (CheckConstraint("Annual_Qty >= 0", name="qty"),)

    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"), primary_key=True)
    Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), primary_key=True)
    Annual_Qty: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    Source: Mapped[str] = mapped_column(String(12), server_default="MANUAL")
