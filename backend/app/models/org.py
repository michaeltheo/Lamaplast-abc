
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    ACTIVITY_LEVELS,
    ACTIVITY_STATUSES,
    CC_TYPES,
    sql_in,
)
from .mixins import AuditMixin, flag, surrogate_pk


# Cost Centers Table (tbl_cost_centers)
class CostCenters(AuditMixin,Base):
    __tablename__ = 'tbl_cost_centers'
    __table_args__ = (CheckConstraint(sql_in("CC_Type", CC_TYPES), name="cc_type"),)

    CC_ID: Mapped[int] = mapped_column(SmallInteger,primary_key=True,autoincrement=True)
    CC_Code: Mapped[str] = mapped_column(String(5),unique=True)
    CC_Name: Mapped[str] = mapped_column(Unicode(50))
    Functional_Direction: Mapped[str] = mapped_column(Unicode(20))
    CC_Type: Mapped[str] = mapped_column(String(12))
    Is_Primary:Mapped[bool] = flag(True)
    Allocation_Method: Mapped[str | None]  = mapped_column(Unicode(30))
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    activities: Mapped[list["Activity"]] = relationship(back_populates="cost_center")


# Activity Table (tbl_activity)
class Activity(AuditMixin, Base):
    __tablename__ = 'tbl_activity'
    __table_args__ = (
        CheckConstraint(sql_in("Activity_Level", ACTIVITY_LEVELS), name="activity_level"),
        CheckConstraint(sql_in("Status", ACTIVITY_STATUSES), name="status"),
        )

    Activity_ID: Mapped[int] = surrogate_pk()
    Activity_Code: Mapped[str] = mapped_column(String(12), unique=True)
    Activity_Name: Mapped[str] = mapped_column(Unicode(60))
    CC_ID: Mapped[int] = mapped_column(ForeignKey('tbl_cost_centers.CC_ID'),index=True)
    Activity_Level: Mapped[str] = mapped_column(String(10))
    ABC_Role: Mapped[str] = mapped_column(Unicode(25))
    Driver_Name: Mapped[str] = mapped_column(Unicode(40))               
    Driver_UoM: Mapped[str] = mapped_column(Unicode(20))                 
    Status: Mapped[str] = mapped_column(String(10), server_default="PENDING")  
    Is_Active: Mapped[bool] = flag(True)
    Notes: Mapped[str | None] = mapped_column(Unicode(200))

    cost_center: Mapped[CostCenters] = relationship(back_populates="activities")