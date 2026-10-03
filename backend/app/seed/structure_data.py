"""Δεδομένα για τη δομή ABC: κέντρα κόστους, δραστηριότητες, πόροι, σενάρια, κατανομές.

Πηγή: LAMAPLAST_DDL_v1.0.sql (τα INSERT της Lamaplast).

ΠΡΟΣΟΧΗ: δεν γράφουμε ποτέ ID (CC_ID, Scenario_ID, ...) — τα δίνει η βάση.
Συνδέουμε πάντα με ΚΩΔΙΚΟ, και το run.py βρίσκει το ID.
"""
from .lookups_data import _rows

# tbl_CostCenters — κλειδί: CC_Code
COST_CENTERS = _rows(
    ("CC_Code", "CC_Name", "Functional_Direction", "CC_Type", "Is_Primary", "Allocation_Method", "Notes"),
    [
        ("1.1", "General Management",      "Διοικητική",  "OVERHEAD",   True,  "% Fixed",       "Γενική Διεύθυνση"),
        ("2.1", "Injection Production",    "Παραγωγική",  "PRODUCTION", True,  "Machine Hours", "Κύριο παραγωγικό CC"),
        ("2.2", "Toolshop / Μηχανουργείο", "Παραγωγική",  "PRODUCTION", True,  "Labor Hours",   "Κατασκευή & συντήρηση καλουπιών"),
        ("3.1", "Logistics / Warehouse",   "Υποστηρικτ.", "SUPPORT",    True,  "Driver-Based",  "Αποθήκευση, picking"),
        ("3.2", "Transport / Διανομές",    "Υποστηρικτ.", "SUPPORT",    True,  "PALLET_KM",     "Στόλος, 3PL"),
        ("4.1", "Sales, Marketing & CS",   "Εμπορική",    "COMMERCIAL", True,  "Orders",        "Πωλήσεις, marketing"),
        ("5.1", "IT",                      "Υποστηρικτ.", "SUPPORT",    False, "FTE",           "Επιμερίζεται στα Primary CC"),
        ("5.2", "HR",                      "Υποστηρικτ.", "SUPPORT",    False, "FTE",           "Επιμερίζεται στα Primary CC"),
        ("5.3", "Finance & Accounting",    "Υποστηρικτ.", "SUPPORT",    False, "% Fixed",       "Επιμερίζεται στα Primary CC"),
    ],
)

# tbl_Activities — κλειδί: Activity_Code  (γράφεις «CC_Code», όχι CC_ID)
ACTIVITIES = _rows(
    ("Activity_Code", "Activity_Name", "CC_Code", "Activity_Level", "ABC_Role", "Driver_Name", "Driver_UoM", "Notes"),
    [
        ("1.1.0.01", "Strategic Planning",          "1.1", "FACILITY", "Administrative", "Admin Hours",       "h",      None),
        ("1.1.0.02", "Corporate Governance",        "1.1", "FACILITY", "Administrative", "Admin Hours",       "h",      None),
        ("2.1.1.01", "Injection Machine Running",   "2.1", "UNIT",     "Production",     "Machine Hours",     "h",      "Κύρια παραγωγική activity"),
        ("2.1.1.02", "Mould Setup",                 "2.1", "BATCH",    "Production",     "Setups",            "τεμ.",   "Αλλαγές καλουπιών"),
        ("2.1.1.03", "Quality Check (Injection)",   "2.1", "BATCH",    "Support",        "QC Weighted Hours", "h",      "QC Factor 1-3 ανά καλούπι"),
        ("2.1.1.04", "Material Feeding & Prep",     "2.1", "UNIT",     "Support",        "KG Processed",      "kg",     None),
        ("2.2.0.01", "CNC Machining",               "2.2", "UNIT",     "Production",     "Labor Hours",       "h",      None),
        ("2.2.0.02", "Hand Finishing",              "2.2", "UNIT",     "Production",     "Labor Hours",       "h",      None),
        ("2.2.0.03", "Tool Assembly",               "2.2", "BATCH",    "Production",     "Assemblies",        "τεμ.",   None),
        ("2.2.0.04", "Tool Maintenance",            "2.2", "PRODUCT",  "Support",        "Maintenance Hours", "h",      "43% κόστους μηχαν/γείου"),
        ("3.1.0.01", "Warehouse Storage",           "3.1", "FACILITY", "Support",        "Pallet Positions",  "τεμ.",   None),
        ("3.1.0.03", "Order Picking",               "3.1", "BATCH",    "Support",        "Orders",            "τεμ.",   None),
        ("3.1.0.04", "Receiving & Inspection",      "3.1", "BATCH",    "Support",        "Inbound Deliveries", "τεμ.",  None),
        ("3.1.0.05", "Palletizing",                 "3.1", "BATCH",    "Support",        "LU3 Count",         "τεμ.",   None),
        ("3.2.0.01", "Customer Deliveries",         "3.2", "BATCH",    "Commercial",     "Deliveries",        "τεμ.",   None),
        ("3.2.0.04", "Linehaul Transport",          "3.2", "UNIT",     "Support",        "PALLET_KM",         "plt·km", None),
        ("4.1.0.01", "Customer Acquisition",        "4.1", "FACILITY", "Commercial",     "Sales Hours",       "h",      None),
        ("4.1.0.02", "Order Management",            "4.1", "BATCH",    "Commercial",     "Orders",            "τεμ.",   None),
        ("4.1.0.04", "Customer Support",            "4.1", "UNIT",     "Commercial",     "Tickets",           "τεμ.",   None),
        ("5.1.0.01", "IT Infrastructure Support",   "5.1", "FACILITY", "Facility Sust.", "FTE",               "FTE",    "Επιμερίζεται από CC7"),
        ("5.2.0.01", "Recruitment & Onboarding",    "5.2", "BATCH",    "Administrative", "FTE",               "FTE",    None),
        ("5.2.0.02", "Payroll & HR Administration", "5.2", "FACILITY", "Administrative", "FTE",               "FTE",    None),
        ("5.3.0.01", "Accounting & Bookkeeping",    "5.3", "FACILITY", "Administrative", "Invoices",          "τεμ.",   None),
        ("5.3.0.03", "Cost Controlling",            "5.3", "FACILITY", "Administrative", "Admin Hours",       "h",      None),
    ],
)

# tbl_Resources — κλειδί: Resource_Code  (δεν υπάρχουν στο DDL — θα συμπληρωθούν)
#   Resource_Code* (≤20 χαρ.)  Resource_Name*  CC_Code*  Resource_Type*  Is_Active  Notes
#   Resource_Type: LABOR | MACHINE | BUILDING | OVERHEAD | COMMERCIAL | ADMIN
#   π.χ. {"Resource_Code": "RES-INJ-LAB", "Resource_Name": "Προσωπικό ενέσιμων", "CC_Code": "2.1", "Resource_Type": "LABOR"}
RESOURCES: list[dict] = []

# tbl_Scenarios — κλειδί: Scenario_Name
# «Base» = όνομα άλλου σεναρίου από αυτή τη λίστα (ή None). Μόνο ΕΝΑ μπορεί να έχει Is_Baseline=True.
SCENARIOS = _rows(
    ("Scenario_Name", "Scenario_Type", "Period_Year", "Is_Baseline", "Is_Locked", "Base", "Description"),
    [
        ("Budget 2025", "BUDGET", 2025, True,  True,  None,          "Προϋπολογισμός 2025 — Base scenario (locked)"),
        ("Actual 2025", "ACTUAL", 2025, False, False, "Budget 2025", "Απολογισμός 2025 — ενημερώνεται περιοδικά"),
    ],
)

# Σε ποιο σενάριο ανήκουν οι κατανομές του RESOURCE_ACTIVITY (πρέπει να υπάρχει στο SCENARIOS)
ALLOCATION_SCENARIO = "Budget 2025"

# tbl_ResourceActivities — πόσο % κάθε πόρου πάει σε κάθε δραστηριότητα (δεν υπάρχουν στο DDL).
# Για κάθε πόρο, τα Share_Pct πρέπει να αθροίζουν 1 (=100%) — το run.py το ελέγχει.
#   π.χ. {"Resource": "RES-INJ-LAB", "Activity": "2.1.1.01", "Share_Pct": Decimal("0.80"), "Allocation_Basis": "Ώρες"}
RESOURCE_ACTIVITY: list[dict] = []
