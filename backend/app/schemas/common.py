from datetime import datetime
from decimal import Decimal
from typing import Annotated, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Ίδια ακρίβεια με τις στήλες: Numeric(12, 2) για ποσά, Numeric(5, 4) για ποσοστά 0–1
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Pct = Annotated[Decimal, Field(ge=0, le=1, max_digits=5, decimal_places=4)]
NotesText = Annotated[str, Field(max_length=200)]


class OrmOut(BaseModel):
    """Βάση για κάθε *Out: διαβάζει τις τιμές κατευθείαν από αντικείμενο SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)


class AuditedOut(OrmOut):
    """Τα πεδία audit: τα γεμίζει το API, ο client μόνο τα διαβάζει."""
    Created_At: datetime
    Created_By: str | None
    Updated_At: datetime | None
    Updated_By: str | None


class PatchModel(BaseModel):
    """Βάση για κάθε *Update: όλα προαιρετικά, αλλάζουν μόνο όσα στάλθηκαν.
    null σε προαιρετική στήλη = «σβήσε την τιμή»· στα required_fields δεν έχει νόημα."""
    required_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def required_columns_cannot_be_cleared(self) -> Self:
        for field in sorted(self.model_fields_set & self.required_fields):
            if getattr(self, field) is None:
                raise ValueError(f"Το πεδίο {field} δεν μπορεί να είναι κενό")
        return self
