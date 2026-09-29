from datetime import datetime
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import Boolean, DateTime,Integer,String,func,text
from sqlalchemy.dialects.mssql import DATETIME2

UtcDateTime=DateTime().with_variant(DATETIME2(0),"mssql")

def flag(default: bool):
    return mapped_column(Boolean, nullable=False, default=default,
                         server_default=text("1" if default else "0"))


def surrogate_pk():
    return mapped_column(Integer, primary_key=True, autoincrement=True)


class AuditMixin:
    Created_At: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.sysutcdatetime(), nullable=False)
    Created_By: Mapped[str | None] = mapped_column(String(50))
    Updated_At: Mapped[datetime | None] = mapped_column(UtcDateTime, onupdate=func.sysutcdatetime())
    Updated_By: Mapped[str | None] = mapped_column(String(50))