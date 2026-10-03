from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import DATA_SOURCES, sql_in
from .mixins import AuditMixin, surrogate_pk


class GLFmeriLine(AuditMixin, Base):
    __tablename__ = "tbl_GLFmeriLines"
    __table_args__ = (
        UniqueConstraint("Scenario_ID", "GL_Account"),
        CheckConstraint(sql_in("Source", DATA_SOURCES), name="source"),
    )

    GL_Line_ID: Mapped[int] = surrogate_pk()
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"), index=True)
    GL_Account: Mapped[str] = mapped_column(String(20))
    GL_Description: Mapped[str | None] = mapped_column(Unicode(100))
    Total_Amount_EUR: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    Source: Mapped[str] = mapped_column(String(12), server_default="MANUAL")
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    allocations: Mapped[list["GLFmeriAllocation"]] = relationship(back_populates="line", cascade="all, delete-orphan")


class GLFmeriAllocation(AuditMixin, Base):
    __tablename__ = "tbl_GLFmeriAllocations"
    __table_args__ = (UniqueConstraint("GL_Line_ID", "CC_ID", "Resource_ID"),)

    GL_Alloc_ID: Mapped[int] = surrogate_pk()
    GL_Line_ID: Mapped[int] = mapped_column(ForeignKey("tbl_GLFmeriLines.GL_Line_ID", ondelete="CASCADE"), index=True)
    CC_ID: Mapped[int] = mapped_column(ForeignKey("tbl_CostCenters.CC_ID"))
    Resource_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Resources.Resource_ID"))  # NULL = overhead του CC
    Amount_EUR: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    line: Mapped[GLFmeriLine] = relationship(back_populates="allocations")


class DriverValue(AuditMixin, Base):
    __tablename__ = "tbl_DriverValues"
    __table_args__ = (
        UniqueConstraint("Scenario_ID", "Activity_ID"),
        CheckConstraint("Driver_Quantity >= 0", name="qty"),
        CheckConstraint(sql_in("Source", DATA_SOURCES), name="source"),
    )

    Driver_Value_ID: Mapped[int] = surrogate_pk()
    Scenario_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Scenarios.Scenario_ID", ondelete="CASCADE"))
    Activity_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Activities.Activity_ID"), index=True)
    Driver_Quantity: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    Is_Practical_Capacity: Mapped[bool | None] = mapped_column()      
    Source: Mapped[str] = mapped_column(String(12), server_default="MANUAL")
    Reason: Mapped[str | None] = mapped_column(Unicode(200))
