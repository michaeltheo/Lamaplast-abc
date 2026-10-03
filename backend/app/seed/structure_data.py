"""Δεδομένα για τη δομή ABC: κέντρα κόστους, δραστηριότητες, πόροι, σενάρια, κατανομές.

Κάθε λίστα = ένας πίνακας, κάθε dict = μία γραμμή.
(*) = υποχρεωτικό. Τα παραδείγματα είναι σε σχόλια — αντικατέστησέ τα με τα πραγματικά δεδομένα.

ΠΡΟΣΟΧΗ: δεν γράφουμε ποτέ ID (CC_ID, Scenario_ID, ...) — τα δίνει η βάση.
Συνδέουμε πάντα με ΚΩΔΙΚΟ, και το run.py βρίσκει το ID.
"""
from decimal import Decimal

# tbl_CostCenters — κλειδί: CC_Code
COST_CENTERS: list[dict] = [
    # {"CC_Code": "PRD01", "CC_Name": "Ενέσιμα", "Functional_Direction": "Παραγωγή", "CC_Type": "PRODUCTION"},
    #   CC_Code* (5 χαρ.)  CC_Name*  Functional_Direction*  CC_Type*  Is_Primary  Allocation_Method  Is_Active  Notes
    #   CC_Type: PRODUCTION | SUPPORT | COMMERCIAL | OVERHEAD
]

# tbl_Activities — κλειδί: Activity_Code  (γράφεις «CC_Code», όχι CC_ID)
ACTIVITIES: list[dict] = [
    # {"Activity_Code": "ACT-INJ-RUN", "Activity_Name": "Λειτουργία ενέσιμων", "CC_Code": "PRD01",
    #  "Activity_Level": "UNIT", "ABC_Role": "Κύρια", "Driver_Name": "Ώρες μηχανής", "Driver_UoM": "h"},
    #   Activity_Code* (≤12 χαρ.)  Activity_Name*  CC_Code*  Activity_Level*  ABC_Role*  Driver_Name*  Driver_UoM*
    #   Status  Is_Active  Notes
    #   Activity_Level: UNIT | BATCH | PRODUCT | FACILITY
    #   Status: PENDING (προεπιλογή) | CONFIRMED | MODIFIED | DELETED | NEW
]

# tbl_Resources — κλειδί: Resource_Code  (γράφεις «CC_Code», όχι CC_ID)
RESOURCES: list[dict] = [
    # {"Resource_Code": "RES-INJ-LAB", "Resource_Name": "Προσωπικό ενέσιμων", "CC_Code": "PRD01",
    #  "Resource_Type": "LABOR"},
    #   Resource_Code* (≤20 χαρ.)  Resource_Name*  CC_Code*  Resource_Type*  Is_Active  Notes
    #   Resource_Type: LABOR | MACHINE | BUILDING | OVERHEAD | COMMERCIAL | ADMIN
]

# tbl_Scenarios — κλειδί: Scenario_Name
# «Base» = όνομα άλλου σεναρίου από αυτή τη λίστα (ή None). Μόνο ΕΝΑ μπορεί να έχει Is_Baseline=True.
SCENARIOS: list[dict] = [
    # {"Scenario_Name": "Budget 2025", "Scenario_Type": "BUDGET", "Period_Year": 2025, "Is_Baseline": True, "Base": None},
    # {"Scenario_Name": "Budget 2025 - αισιόδοξο", "Scenario_Type": "WHATIF", "Period_Year": 2025, "Base": "Budget 2025"},
    #   Scenario_Name*  Scenario_Type*  Period_Year*  Base  Is_Baseline  Is_Locked  Description
    #   Scenario_Type: BUDGET | ACTUAL | REVISED | WHATIF
]

# Σε ποιο σενάριο ανήκουν οι κατανομές του RESOURCE_ACTIVITY (πρέπει να υπάρχει στο SCENARIOS)
ALLOCATION_SCENARIO = "Budget 2025"

# tbl_ResourceActivities — πόσο % κάθε πόρου πάει σε κάθε δραστηριότητα.
# Για κάθε πόρο, τα Share_Pct πρέπει να αθροίζουν 1 (=100%) — το run.py το ελέγχει.
RESOURCE_ACTIVITY: list[dict] = [
    # {"Resource": "RES-INJ-LAB", "Activity": "ACT-INJ-RUN", "Share_Pct": Decimal("0.80"), "Allocation_Basis": "Ώρες"},
    # {"Resource": "RES-INJ-LAB", "Activity": "ACT-INJ-SET", "Share_Pct": Decimal("0.20"), "Allocation_Basis": "Ώρες"},
    #   Resource* (Resource_Code)  Activity* (Activity_Code)  Share_Pct* (0 < x ≤ 1)  Allocation_Basis
]
