from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Unicode,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import BOM_COMPONENT_TYPES, BOM_STATUSES, sql_in
from .mixins import AuditMixin, flag, surrogate_pk


class BOM(AuditMixin, Base):
    __tablename__ = "tbl_BOM"
    __table_args__ = (
        UniqueConstraint("Parent_Item_ID", "BOM_Version"),
        CheckConstraint(sql_in("Status", BOM_STATUSES), name="status"),
        CheckConstraint("Valid_To IS NULL OR Valid_To >= Valid_From", name="valid_range"),
        Index("UX_tbl_BOM_one_active", "Parent_Item_ID", unique=True, mssql_where=text("Status = 'ACTIVE'")),
    )

    BOM_ID: Mapped[int] = surrogate_pk()
    Parent_Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), index=True)
    BOM_Version: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    Status: Mapped[str] = mapped_column(String(10), server_default="DRAFT")   
    BOM_Name: Mapped[str | None] = mapped_column(Unicode(80))
    Valid_From: Mapped[date | None] = mapped_column(Date)
    Valid_To: Mapped[date | None] = mapped_column(Date)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    lines: Mapped[list["BOMLine"]] = relationship(
        back_populates="bom", cascade="all, delete-orphan", order_by="BOMLine.Sequence")


class BOMLine(AuditMixin, Base):
    __tablename__ = "tbl_BOMLines"
    __table_args__ = (
        CheckConstraint(sql_in("Component_Type", BOM_COMPONENT_TYPES), name="component_type"),
        CheckConstraint("Qty > 0", name="qty"),
        CheckConstraint("Scrap_Pct IS NULL OR Scrap_Pct BETWEEN 0 AND 1", name="scrap"),
    )

    BOM_Line_ID: Mapped[int] = surrogate_pk()
    BOM_ID: Mapped[int] = mapped_column(ForeignKey("tbl_BOM.BOM_ID", ondelete="CASCADE"), index=True)
    Sequence: Mapped[int] = mapped_column(SmallInteger, server_default="10")
    Component_Type: Mapped[str] = mapped_column(String(20))
    Child_Item_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Items.Item_ID"), index=True)  
    Qty: Mapped[Decimal] = mapped_column(Numeric(14, 6))         
    Scrap_Pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    Is_Optional: Mapped[bool] = flag(False)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    bom: Mapped[BOM] = relationship(back_populates="lines")
