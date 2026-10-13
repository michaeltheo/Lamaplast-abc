from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import DATA_SOURCES
from app.schemas.common import AuditedOut, NotesText, OrmOut

DataSource = Literal[*DATA_SOURCES]
Price5 = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=5)]     # Numeric(14, 5)


class _Period(BaseModel):
    Valid_From: date
    Valid_To: date | None = None      # κενό = ισχύει ακόμα

    @model_validator(mode="after")
    def to_is_not_before_from(self) -> Self:
        if self.Valid_To is not None and self.Valid_To < self.Valid_From:
            raise ValueError("Το Valid_To δεν μπορεί να είναι πριν από το Valid_From")
        return self


class _HistoryPatch(BaseModel):
    """Η τιμή δεν διορθώνεται: νέα τιμή = νέα γραμμή. Άγνωστα πεδία (π.χ. Price_EUR) απορρίπτονται με 422."""
    model_config = ConfigDict(extra="forbid")


# --- τιμές αγοράς ---

class PriceCreate(_Period):
    Item_ID: int
    Scenario_ID: int
    Price_EUR: Price5 | None = None   # σε ξένο νόμισμα μπορεί να λείπει: υπολογίζεται από Price_Local / FX_Rate
    Currency: str = Field(default="EUR", pattern="^[A-Za-z]{3}$")
    FX_Rate: Decimal = Field(default=Decimal(1), gt=0, max_digits=12, decimal_places=6)   # ξένο νόμισμα ανά 1 EUR
    Price_Local: Price5 | None = None
    Supplier: str | None = Field(default=None, max_length=100)
    Source: DataSource = "MANUAL"
    Reason: NotesText | None = None

    @field_validator("Currency")
    @classmethod
    def upper(cls, value: str) -> str:
        return value.upper()


class PriceUpdate(_HistoryPatch):
    Reason: NotesText | None = None
    Supplier: str | None = Field(default=None, max_length=100)
    Valid_To: date | None = None


class PriceOut(AuditedOut):
    Price_ID: int
    Item_ID: int
    Scenario_ID: int
    Valid_From: date
    Valid_To: date | None
    Price_EUR: Decimal
    Currency: str
    FX_Rate: Decimal
    Price_Local: Decimal | None
    Supplier: str | None
    Source: str
    Reason: str | None


# --- τιμές πώλησης ---

class SalesPriceCreate(_Period):
    Item_ID: int
    Customer_ID: int | None = None    # κενό = γενική τιμή, για όλους τους πελάτες
    Scenario_ID: int
    Price_EUR: Price5
    Source: DataSource = "MANUAL"
    Reason: NotesText | None = None


class SalesPriceUpdate(_HistoryPatch):
    Reason: NotesText | None = None
    Valid_To: date | None = None


class SalesPriceOut(AuditedOut):
    Sales_Price_ID: int
    Item_ID: int
    Customer_ID: int | None
    Scenario_ID: int
    Valid_From: date
    Valid_To: date | None
    Price_EUR: Decimal
    Source: str
    Reason: str | None


# --- ετήσιοι όγκοι ---

class ItemVolumeIn(BaseModel):
    Item_ID: int
    Annual_Qty: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    Source: DataSource = "MANUAL"


class ItemVolumeOut(OrmOut):
    Scenario_ID: int
    Item_ID: int
    Annual_Qty: Decimal
    Source: str
