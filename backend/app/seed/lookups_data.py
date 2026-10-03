"""Δεδομένα για τους πίνακες ταξινόμησης.

Κάθε λίστα = ένας πίνακας, κάθε dict = μία γραμμή.
Τα κλειδιά είναι ακριβώς τα ονόματα των στηλών του model.
(*) = υποχρεωτικό. Όσα λείπουν παίρνουν την προεπιλογή της βάσης ή μένουν κενά.
Τα παραδείγματα είναι σε σχόλια — αντικατέστησέ τα με τα πραγματικά δεδομένα.
"""
from decimal import Decimal

# tbl_GlobalDefaults — κλειδί: Parameter
GLOBAL_DEFAULTS: list[dict] = [
    # {"Parameter": "ENERGY_EUR_KWH", "Value": Decimal("0.15"), "Unit": "€/kWh", "Description": "Κόστος ρεύματος"},
    #   Parameter*  Value*  Unit  Description
]

# tbl_ItemCodeRules — κλειδί: Prefix
ITEM_CODE_RULES: list[dict] = [
    # {"Prefix": "RM", "Description": "Πρώτες ύλες", "Item_Type": "RAW_MAT", "BOM_Role": "INPUT",
    #  "Material_Source": "LAMAPLAST"},
    #   Prefix*  Description*  Item_Type*  BOM_Role*  Material_Source  Zero_Cost  ABC_Component_Type
    #   Is_Regrind_Source  Regrind_Value_Override  Notes
    #   Item_Type: RAW_MAT | AUXILIARY | PACKAGING | FG | FG_FASON | SF | COMPONENT | MOULD
    #   BOM_Role: INPUT | OUTPUT | BOTH        Material_Source: LAMAPLAST | CUSTOMER
]

# tbl_BaseMaterials — κλειδί: Material_Code
BASE_MATERIALS: list[dict] = [
    # {"Material_Code": "PP", "Material_Name": "Πολυπροπυλένιο", "Material_Family": "THERMOPLASTIC",
    #  "Default_Regrind_Recovery": Decimal("0.95"), "Default_Regrind_Value": Decimal("0.50")},
    #   Material_Code*  Material_Name*  Material_Family*  Is_Recyclable  Default_Regrind_Recovery
    #   Default_Regrind_Value  Is_Active  Notes
    #   Material_Family: THERMOPLASTIC | METAL | WOOD | COMPOSITE | OTHER
    #   Regrind τιμές: 0 έως 1
]

# tbl_BSSG — κλειδί: BSSG_Code
BSSG_ROWS: list[dict] = [
    # {"BSSG_Code": "HW", "BSSG_Name": "Houseware", "Sort_order": 1},
    #   BSSG_Code* (2 χαρ.)  BSSG_Name*  Sort_order  Is_Active
]

# tbl_CommercialPillars — κλειδί: Pillar_Code  (το BSSG_Code πρέπει να υπάρχει στο BSSG_ROWS)
PILLARS: list[dict] = [
    # {"Pillar_Code": "KITCHEN", "Pillar_Name": "Κουζίνα", "BSSG_Code": "HW", "Sort_order": 1},
    #   Pillar_Code*  Pillar_Name*  BSSG_Code*  Sort_order  Is_Active
]

# tbl_ProductGroups — κλειδί: Group_Code  (το Pillar_Code πρέπει να υπάρχει στο PILLARS)
GROUPS: list[dict] = [
    # {"Group_Code": "KIT-BOX", "Group_Name": "Δοχεία τροφίμων", "Pillar_Code": "KITCHEN", "Sort_Order": 1},
    #   Group_Code*  Group_Name*  Pillar_Code*  Sort_Order  Is_Active
]

# tbl_MachineCategories — κλειδί: Category_Code
MACHINE_CATEGORIES: list[dict] = [
    # {"Category_Code": "INJ-S", "Category_Name": "Ενέσιμες μικρές", "Machine_Group": "INJECTION",
    #  "Clamp_Force_Min_tn": 50, "Clamp_Force_Max_tn": 200},
    #   Category_Code*  Category_Name*  Machine_Group  Clamp_Force_Min_tn  Clamp_Force_Max_tn  Notes
    #   Machine_Group: INJECTION | AUXILIARY | TOOLSHOP
]

# tbl_Customers — κλειδί: Customer_Code
CUSTOMERS: list[dict] = [
    # {"Customer_Code": "C0001", "Customer_Name": "Πελάτης Α.Ε."},
    #   Customer_Code*  Customer_Name*  Is_Internal  Is_Active  Notes
]
