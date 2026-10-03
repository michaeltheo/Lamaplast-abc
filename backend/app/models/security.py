from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, SmallInteger, String, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import AUDIT_ACTIONS, MODULES, USER_ROLES, sql_in
from .mixins import AuditMixin, UtcDateTime, flag, surrogate_pk


# `tbl_Users` Table (Users)
class User(AuditMixin, Base):
    __tablename__ = "tbl_Users"
    __table_args__ = (CheckConstraint(sql_in("Role", USER_ROLES), name="role"),)

    User_ID: Mapped[int] = surrogate_pk()
    Username: Mapped[str] = mapped_column(String(50), unique=True)
    Full_Name: Mapped[str] = mapped_column(Unicode(100))
    Email: Mapped[str | None] = mapped_column(String(120))
    Password_Hash: Mapped[str] = mapped_column(String(255))       
    Role: Mapped[str] = mapped_column(String(10), server_default="USER")
    Is_Active: Mapped[bool] = flag(True)
    Must_Change_Password: Mapped[bool] = flag(True)
    Failed_Logins: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    Locked_Until: Mapped[datetime | None] = mapped_column(UtcDateTime)
    Last_Login_At: Mapped[datetime | None] = mapped_column(UtcDateTime)

    permissions: Mapped[list["UserPermission"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)

# User Permissions Table (tbl_UserPermissions)
class UserPermission(AuditMixin, Base):
    __tablename__ = "tbl_UserPermissions"
    __table_args__ = (CheckConstraint(sql_in("Module", MODULES), name="module"),)

    User_ID: Mapped[int] = mapped_column(ForeignKey("tbl_Users.User_ID", ondelete="CASCADE"), primary_key=True)
    Module: Mapped[str] = mapped_column(String(20), primary_key=True)
    Can_Edit: Mapped[bool] = flag(True)          # 0 = μόνο ανάγνωση

# Audit Log Table (tbl_AuditLog)
class AuditLog(Base):
    __tablename__ = "tbl_AuditLog"
    __table_args__ = (
        CheckConstraint(sql_in("Action", AUDIT_ACTIONS), name="action"),
        Index("IX_tbl_AuditLog_record", "Table_Name", "Record_Key"),
        Index("IX_tbl_AuditLog_at", "At"),
    )

    Audit_ID: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    At: Mapped[datetime] = mapped_column(UtcDateTime, server_default=func.sysutcdatetime())
    User_ID: Mapped[int | None] = mapped_column(ForeignKey("tbl_Users.User_ID"))
    Username: Mapped[str | None] = mapped_column(String(50))     
    Action: Mapped[str] = mapped_column(String(15))
    Table_Name: Mapped[str | None] = mapped_column(String(60))
    Record_Key: Mapped[str | None] = mapped_column(String(60))    # π.χ. "Item_ID=42"
    Changes_JSON: Mapped[str | None] = mapped_column(UnicodeText)  # {"Price_EUR": [1.45, 1.52]}
    Notes: Mapped[str | None] = mapped_column(Unicode(200))
