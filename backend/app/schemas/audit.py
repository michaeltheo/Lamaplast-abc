from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Audit_ID: int
    At: datetime
    User_ID: int | None
    Username: str | None
    Action: str
    Table_Name: str | None
    Record_Key: str | None
    Changes_JSON: str | None
    Notes: str | None
