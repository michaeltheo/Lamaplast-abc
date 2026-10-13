from decimal import Decimal
from typing import Annotated, Literal

from app.schemas.common import AuditedOut, Money, NotesText, PatchModel, Pct
from pydantic import BaseModel, Field

# Το model δεν έχει CHECK για το Ownership και γράφει το Cost_Basis μέσα στο CHECK, όχι στο enums.py.
# Μέχρι να μπουν εκεί (βλ. «προτεινόμενες αλλαγές στο σχήμα»), οι επιτρεπτές τιμές ορίζονται εδώ.
OWNERSHIPS = ("ΙΔΙΟΚΤΗΤΟ", "ΜΙΣΘΩΜΕΝΟ")
COST_BASES = ("m2", "m3")

Area = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Height = Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)]


class BuildingCreate(BaseModel):
    Building_Code: str = Field(min_length=1, max_length=15)
    Zone_Name: str | None = Field(default=None, min_length=1, max_length=40)
    Ownership: Literal[*OWNERSHIPS] = "ΙΔΙΟΚΤΗΤΟ"
    Floor_Level: int = Field(default=0, ge=-10, le=200)
    Area_m2: Area | None = None
    Height_m: Height | None = None
    Utilization_Pct: Pct | None = None
    Cost_Basis: Literal[*COST_BASES] = "m2"
    CC_ID: int
    Resource_ID: int | None = None
    Depreciation_EUR: Money = Decimal(0)
    Equipment_Depr_EUR: Money = Decimal(0)
    IT_Depr_EUR: Money = Decimal(0)
    Notes: NotesText | None = None


class BuildingUpdate(PatchModel):
    required_fields = frozenset({"Building_Code", "Ownership", "Floor_Level", "Cost_Basis", "CC_ID",
                                 "Depreciation_EUR", "Equipment_Depr_EUR", "IT_Depr_EUR"})

    Building_Code: str | None = Field(default=None, min_length=1, max_length=15)
    Zone_Name: str | None = Field(default=None, min_length=1, max_length=40)
    Ownership: Literal[*OWNERSHIPS] | None = None
    Floor_Level: int | None = Field(default=None, ge=-10, le=200)
    Area_m2: Area | None = None
    Height_m: Height | None = None
    Utilization_Pct: Pct | None = None
    Cost_Basis: Literal[*COST_BASES] | None = None
    CC_ID: int | None = None
    Resource_ID: int | None = None
    Depreciation_EUR: Money | None = None
    Equipment_Depr_EUR: Money | None = None
    IT_Depr_EUR: Money | None = None
    Notes: NotesText | None = None


class BuildingOut(AuditedOut):
    Building_ID: int
    Building_Code: str
    Zone_Name: str | None
    Ownership: str
    Floor_Level: int
    Area_m2: Decimal | None
    Height_m: Decimal | None
    Utilization_Pct: Decimal | None
    Nominal_Volume_m3: Decimal | None   # υπολογίζεται από τη βάση
    Useful_Volume_m3: Decimal | None    # υπολογίζεται από τη βάση
    Cost_Basis: str
    CC_ID: int
    Resource_ID: int | None
    Depreciation_EUR: Decimal
    Equipment_Depr_EUR: Decimal
    IT_Depr_EUR: Decimal
    Total_Cost_EUR: Decimal             # υπολογίζεται από τη βάση
    Is_Active: bool
    Notes: str | None
