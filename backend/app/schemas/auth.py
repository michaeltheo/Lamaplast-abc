from datetime import datetime
from typing import Annotated

from app.core.config import settings
from pydantic import BaseModel, ConfigDict, Field

Password = Annotated[str, Field(max_length=128)]
NewPassword = Annotated[str, Field(min_length=settings.min_password_length, max_length=128)]


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: Password


class ChangePasswordIn(BaseModel):
    current_password: Password
    new_password: NewPassword


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Module: str
    Can_Edit: bool


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    User_ID: int
    Username: str
    Full_Name: str
    Email: str | None
    Role: str
    Is_Active: bool
    Must_Change_Password: bool
    Locked_Until: datetime | None
    Last_Login_At: datetime | None
    permissions: list[PermissionOut]
