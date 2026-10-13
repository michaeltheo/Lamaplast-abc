from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import MODULES, USER_ROLES
from app.schemas.auth import NewPassword

RoleName = Literal[*USER_ROLES]


class UserCreate(BaseModel):
    Username: str = Field(min_length=1, max_length=50)
    Full_Name: str = Field(min_length=1, max_length=100)
    Email: str | None = Field(default=None, max_length=120)
    Role: RoleName = "USER"
    password: NewPassword


class UserUpdate(BaseModel):
    Full_Name: str | None = Field(default=None, min_length=1, max_length=100)
    Email: str | None = Field(default=None, max_length=120)
    Role: RoleName | None = None
    Is_Active: bool | None = None
    password: NewPassword | None = None
    unlock: bool = False


class PermissionIn(BaseModel):
    Module: Literal[*MODULES]
    Can_Edit: bool = True
