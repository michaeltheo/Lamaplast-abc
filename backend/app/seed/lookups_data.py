"""Δεδομένα για τους πίνακες ταξινόμησης.

Πηγή: LAMAPLAST_DDL_v1.0.sql (τα INSERT της Lamaplast).

Κάθε πίνακας γράφεται σαν «πίνακας Excel»: πρώτα τα ονόματα των στηλών,
μετά μία γραμμή ανά εγγραφή. Η _rows() τα κάνει λίστα από dict
(π.χ. {"BSSG_Code": "01", "BSSG_Name": "Αξεσουάρ-Σιφόν", ...}) για το run.py.
"""
from decimal import Decimal as D


def _rows(columns: tuple[str, ...], data: list[tuple]) -> list[dict]:
    return [dict(zip(columns, row, strict=True)) for row in data]


# tbl_GlobalDefaults — κλειδί: Parameter
GLOBAL_DEFAULTS = _rows(
    ("Parameter", "Value", "Description"),
    [
        ("Regrind_Recovery_Pct",     D("0.850000"), "Ποσοστό ανάκτησης sprue+scrap (global default)"),
        ("Regrind_Value_Pct",        D("0.650000"), "Αξία regrind ως % virgin (global default)"),
        ("Scrap_Pct_Default",        D("0.041000"), "Φύρα τεμαχίων % (από δείκτες 2004)"),
        ("Productivity_Factor",      D("0.975000"), "Παραγωγικότητα μηχανών (100%-2.5% βλάβες)"),
        ("Labor_Utilization_Rate",   D("0.947000"), "Βαθμός απασχόλησης χειριστών 2025"),
        ("Setup_Time_Default_Min",   D("41.000000"), "Πρότυπος χρόνος setup (λεπτά, ανάλυση 2004)"),
        ("Setdown_Time_Default_Min", D("22.000000"), "Πρότυπος χρόνος setdown (λεπτά)"),
        ("KWh_Price_EUR",            D("0.180000"), "Τιμή ΔΕΗ €/KWh (να ενημερώνεται)"),
        ("Sales_Marketing_Pct",      D("0.140000"), "Sales & Marketing % επί full cost"),
        ("MB_Regrind_Value_Pct",     D("0.200000"), "Αξία regrind masterbatch vs virgin"),
    ],
)

# tbl_ItemCodeRules — κλειδί: Prefix
ITEM_CODE_RULES = _rows(
    ("Prefix", "Description", "Item_Type", "Material_Source", "Zero_Cost", "BOM_Role",
     "ABC_Component_Type", "Is_Regrind_Source", "Regrind_Value_Override", "Notes"),
    [
        ("10",    "Α' Ύλες",                       "RAW_MAT",   "LAMAPLAST", False, "INPUT",  "RAW_MATERIAL",  True,  None,       "Mix% inclusive 100%"),
        ("11",    "Α' Ύλες Πελατών",               "RAW_MAT",   "CUSTOMER",  True,  "INPUT",  "RAW_MATERIAL",  True,  None,       "Τιμή=0"),
        ("12",    "Β' Ύλες / Βοηθητικά",           "AUXILIARY", "LAMAPLAST", False, "INPUT",  "ADDITIVE",      False, D("0.30"), "Εκτός 12699"),
        ("12699", "Χρώματα / Masterbatch",         "AUXILIARY", "LAMAPLAST", False, "INPUT",  "MASTERBATCH",   False, D("0.20"), "Regrind μαζί με PP"),
        ("13",    "Β' Ύλες Πελατών",               "AUXILIARY", "CUSTOMER",  True,  "INPUT",  "ADDITIVE",      False, None,       "Τιμή=0"),
        ("14",    "Συσκευαστικό Είδος",            "PACKAGING", "LAMAPLAST", False, "INPUT",  "PACKAGING_PRI", False, None,       "qty × τιμή"),
        ("30",    "Έτοιμο Προϊόν Lamaplast",       "FG",        "LAMAPLAST", False, "OUTPUT", None,            False, None,       None),
        ("31",    "Προϊόν Φασόν / Δικά μας υλικά", "FG_FASON",  "LAMAPLAST", False, "OUTPUT", None,            False, None,       "Πλήρες BOM cost"),
        ("32",    "Προϊόν Φασόν / Υλικά πελάτη",   "FG_FASON",  "CUSTOMER",  False, "OUTPUT", None,            False, None,       "Υλικά=0"),
        ("33",    "Ημιέτοιμο Προϊόν",              "SF",        "LAMAPLAST", False, "BOTH",   None,            False, None,       None),
        ("34",    "Εξάρτημα Παραγωγής",            "COMPONENT", "LAMAPLAST", False, "BOTH",   None,            False, None,       None),
        ("9801",  "Καλούπια Lamaplast",            "MOULD",     "LAMAPLAST", False, "INPUT",  None,            False, None,       "Απόσβεση κανονική"),
        ("9901",  "Καλούπια Πελατών",              "MOULD",     "CUSTOMER",  True,  "INPUT",  None,            False, None,       "Αποσβέσιμη αξία=0"),
    ],
)

# tbl_BaseMaterials — κλειδί: Material_Code
BASE_MATERIALS = _rows(
    ("Material_Code", "Material_Name", "Material_Family", "Is_Recyclable",
     "Default_Regrind_Recovery", "Default_Regrind_Value", "Notes"),
    [
        ("01", "PP",        "THERMOPLASTIC", True,  None,      None,      "Global defaults OK"),
        ("02", "PS",        "THERMOPLASTIC", True,  D("0.80"), D("0.55"), "Πιο εύθραυστο regrind"),
        ("03", "PVC",       "THERMOPLASTIC", True,  D("0.75"), D("0.50"), "Περιορισμένο regrind"),
        ("04", "ABS",       "THERMOPLASTIC", True,  D("0.80"), D("0.60"), "Μηχ. ιδιότητες υποβαθμ."),
        ("05", "HF",        "THERMOPLASTIC", True,  None,      None,      "High Flow PP variant"),
        ("06", "PA",        "THERMOPLASTIC", True,  D("0.70"), D("0.55"), "Nylon — υγρασία κρίσιμη"),
        ("07", "PE",        "THERMOPLASTIC", True,  None,      None,      "Παρόμοιο με PP"),
        ("08", "PC",        "THERMOPLASTIC", True,  D("0.75"), D("0.55"), "Οπτικές ιδιότητες χάνονται"),
        ("09", "LUR",       "THERMOPLASTIC", True,  D("0.70"), D("0.50"), "Polyurethane"),
        ("10", "PET",       "THERMOPLASTIC", True,  D("0.80"), D("0.60"), None),
        ("11", "PBT",       "THERMOPLASTIC", True,  D("0.75"), D("0.55"), None),
        ("12", "TPE",       "THERMOPLASTIC", True,  D("0.70"), D("0.50"), "Elastomer — δύσκολο"),
        ("13", "TPV",       "THERMOPLASTIC", True,  D("0.65"), D("0.45"), "Vulcanized — δύσκολο"),
        ("14", "TROG",      "THERMOPLASTIC", True,  D("0.75"), D("0.55"), None),
        ("40", "ΧΑΛΥΒΑΣ",   "METAL",         False, None,      None,      "Δεν ισχύει regrind"),
        ("50", "ΣΥΝΘΕΤΙΚΟ", "COMPOSITE",     False, None,      None,      "Case by case"),
        ("51", "ΞΥΛΟ",      "WOOD",          False, None,      None,      None),
        ("52", "ΜΕΤΑΛΟ",    "METAL",         False, None,      None,      None),
        ("53", "ΑΛΟΥΜΙΝΙΟ", "METAL",         False, None,      None,      None),
        ("99", "ΑΔΙΑΦΟΡΟ",  "OTHER",         False, None,      None,      None),
    ],
)

# tbl_BSSG — κλειδί: BSSG_Code
BSSG_ROWS = _rows(
    ("BSSG_Code", "BSSG_Name", "Sort_order"),
    [
        ("01", "Αξεσουάρ-Σιφόν",   1),
        ("02", "Έπιπλα",           2),
        ("03", "Φασόν-Καλούπια",   3),
        ("04", "Συσκευασία",       4),
        ("99", "Άνευ BSSG / Όλα", 99),
    ],
)

# tbl_CommercialPillars — κλειδί: Pillar_Code
PILLARS = _rows(
    ("Pillar_Code", "Pillar_Name", "BSSG_Code", "Sort_order"),
    [
        ("01-1", "Αξεσουάρ Μπάνιου",           "01", 1),
        ("01-2", "Σιφόν",                      "01", 2),
        ("01-3", "Συστήματα Σωλήνων",          "01", 3),
        ("02-1", "Έπιπλα Γηπέδου",             "02", 1),
        ("02-2", "Έπιπλα Indoor",              "02", 2),
        ("02-3", "Έπιπλα Outdoor",             "02", 3),
        ("02-4", "Έπιπλα Συνεδριακά/Catering", "02", 4),
        ("02-5", "Λοιπά Έπιπλα",               "02", 5),
        ("03-1", "Προϊόντα Φασόν",             "03", 1),
        ("03-2", "Προϊόντα Μηχανουργείου",     "03", 2),
        ("04-1", "Τελάρα Νερού HOD",           "04", 1),
        ("04-2", "Παλέτες",                    "04", 2),
        ("04-3", "Πλαστικά Κιβώτια/Τελάρα",    "04", 3),
        ("04-4", "Παλετοκιβώτια",              "04", 4),
        ("04-5", "Λοιπά Προϊόντα Συσκευασίας", "04", 5),
        ("99-0", "Χωρίς Εμπορικό Πυλώνα",      "99", 99),
    ],
)

# tbl_ProductGroups — κλειδί: Group_Code
GROUPS = _rows(
    ("Group_Code", "Group_Name", "Pillar_Code", "Sort_Order"),
    [
        ("01-1-100", "ΚΑΘΡΕΠΤΕΣ",                    "01-1", 1),
        ("01-1-101", "ΚΑΖΑΝΑΚΙΑ",                    "01-1", 2),
        ("01-1-103", "ΚΑΛΥΜΑΤΑ",                     "01-1", 3),
        ("01-1-104", "ΧΑΡΤΟΔΟΧΕΙΑ-ΠΙΓΚΑΛ ΣΕΤ",       "01-1", 4),
        ("01-1-105", "ΠΙΝΑΚΕΣ ΥΔΡΑΥΛΙΚΩΝ",           "01-1", 5),
        ("01-1-106", "ΛΟΙΠΑ ΑΞΕΣΟΥΑΡ",               "01-1", 6),
        ("01-1-109", "ΛΟΙΠΑ-ΔΙΑΦΟΡΑ ΑΞΕΣ ΜΠΑΝΙΟΥ",   "01-1", 7),
        ("01-1-110", "ΚΑΘΡΕΠΤΕΣ-ΝΤΟΥΛΑΠΕΣ ERMAN",    "01-1", 8),
        ("01-1-199", "ΑΝΤΑΛΛΑΚΤΙΚΑ ΛΟΙΠΑ (ΑΞΕΣΟΥΑΡ)", "01-1", 99),
        ("01-2-200", "ΒΑΛΒΙΔΕΣ",                     "01-2", 1),
        ("01-2-201", "ΣΥΝΔΕΣΕΙΣ",                    "01-2", 2),
        ("01-2-202", "ΣΙΦΟΝ ΛΙΠΟΣΥΛΛΕΚΤΕΣ",          "01-2", 3),
        ("01-2-203", "ΣΙΦΟΝ ΝΙΠΤΗΡΟΣ-ΜΠΑΝΙΟΥ",       "01-2", 4),
        ("01-2-204", "ΣΙΦΟΝ ΝΕΡΟΧ.ΣΩΛΗΝΩΤΑ",         "01-2", 5),
        ("01-2-205", "ΣΙΦΟΝ ΔΑΠΕΔΟΥ",                "01-2", 6),
        ("01-2-299", "ΑΝΤΑΛΛΑΚΤΙΚΑ ΛΟΙΠΑ (ΣΙΦΟΝ)",    "01-2", 99),
        ("01-3-001", "ΣΥΣΤΗΜΑΤΑ PP-R (FISCHER)",     "01-3", 1),
        ("02-3-001", "ΠΟΛΥΘΡΟΝΕΣ/ΚΑΡΕΚΛΕΣ",          "02-3", 1),
        ("02-3-002", "ΣΚΑΜΠΩ",                       "02-3", 2),
        ("02-3-003", "ΞΑΠΛΩΣΤΡΕΣ",                   "02-3", 3),
        ("02-3-004", "ΤΡΑΠΕΖΙΑ",                     "02-3", 4),
        ("02-3-005", "ΤΑΒΛΕΣ",                       "02-3", 5),
        ("02-3-006", "ΠΟΔΙΑ-ΒΑΣΕΙΣ",                 "02-3", 6),
        ("02-3-007", "ΚΟΜΠΛΕ ΣΕΤ ΣΑΛΟΝΙΩΝ",          "02-3", 7),
        ("02-3-008", "ΜΑΞΙΛΑΡΙΑ-ΘΗΚΕΣ",              "02-3", 8),
        ("02-3-009", "ΟΜΠΡΕΛΕΣ",                     "02-3", 9),
        ("02-3-099", "ΛΟΙΠΑ ΕΠΙΠΛΑ",                 "02-3", 99),
        ("03-1-001", "ΠΡΟΪΟΝΤΑ ΦΑΣΟΝ",               "03-1", 1),
        ("03-2-001", "ΚΑΛΟΥΠΙΑ-ΜΗΤΡΕΣ ΠΡΟΣ ΠΩΛΗΣΗ",  "03-2", 1),
        ("04-1-710", "ΚΟΥΒΑΔΕΣ",                     "04-1", 1),
        ("04-1-711", "ΤΑΠΕΡ",                        "04-1", 2),
        ("04-2-721", "ΤΕΛΑΡΑ ΕΙΔΙΚΗΣ ΧΡΗΣΗΣ",        "04-2", 1),
        ("04-2-722", "ΚΙΒΩΤΙΑ DELIVERY",             "04-2", 2),
        ("04-2-735", "ΤΕΛΑΡΑ ΜΑΝΑΒΙΚΗΣ",             "04-2", 3),
        ("04-3-731", "ΠΑΛΕΤΕΣ",                      "04-3", 1),
        ("04-3-732", "ΠΑΛΕΤΟΤΕΛΑΡΑ ΝΕΡΟΥ",           "04-3", 2),
        ("04-3-740", "ΤΑΠΕΣ ΡΟΛΛΩΝ ΦΙΛΜ",            "04-3", 3),
        # Στο DDL δείχνει σε πυλώνα "04-9", που δεν υπάρχει → μπαίνει στο "04-5" (Λοιπά Προϊόντα Συσκευασίας)
        ("04-9-799", "ΕΞΑΡΤ-ΑΝΤΑΛ.ΣΥΣΚΕΥΑΣΙΑΣ",      "04-5", 99),
        ("99-0-000", "ΚΕΝΟ",                         "99-0", 99),
    ],
)

# tbl_MachineCategories — κλειδί: Category_Code
# (Machine_Group δεν υπάρχει στο DDL — βγαίνει από την κατηγορία)
MACHINE_CATEGORIES = _rows(
    ("Category_Code", "Category_Name", "Machine_Group", "Clamp_Force_Min_tn", "Clamp_Force_Max_tn", "Notes"),
    [
        ("M1", "Cat1 — <100 tn",          "INJECTION", None, 100,  None),
        ("M2", "Cat2 — 100-200 tn",       "INJECTION", 100,  200,  None),
        ("M3", "Cat3 — 200-350 tn",       "INJECTION", 200,  350,  None),
        ("M4", "Cat4 — 350-600 tn",       "INJECTION", 350,  600,  None),
        ("M5", "Cat5 — >600 tn",          "INJECTION", 600,  None, None),
        ("M6", "Cat6 — Special >1000 tn", "INJECTION", 1000, None, "ITALTECH, KUASY"),
        ("AX", "Auxiliary Injection",     "AUXILIARY", None, None, "Βοηθητικός εξοπλ. injection"),
        ("TL", "Toolshop Equipment",      "TOOLSHOP",  None, None, "Μηχανουργείο"),
    ],
)

# tbl_Customers — κλειδί: Customer_Code
# Οι υπόλοιποι πελάτες θα έρθουν από export του SoftOne.
CUSTOMERS = _rows(
    ("Customer_Code", "Customer_Name", "Is_Internal", "Is_Active", "Notes"),
    [
        ("000", "ΛΑΜΑΠΛΑΣΤ",     True, True, "Internal — δικά μας προϊόντα"),
        ("999", "ΑΔΙΑΦΟΡΟ/ΟΛΟΙ", True, True, "Generic — χωρίς συγκεκριμένο πελάτη"),
    ],
)
