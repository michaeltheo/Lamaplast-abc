# Φάση D · CRUD για τα master δεδομένα

Κατάσταση: ολοκληρώθηκε. `pytest`: 397 passed. `ruff check .`: καθαρό (με το `backend/ruff.toml`).

## Πώς είναι στημένο

- **Router** (`app/routers/`): παραλαβή, κλήση του service, `commit`, απάντηση.
- **Service** (`app/services/`): όλοι οι κανόνες και το audit. Δεν ξέρει τίποτα για FastAPI, ώστε να το καλεί και το Excel import (Φάση E). Ρίχνει `NotFoundError` (404), `ConflictError` (409), `BusinessRuleError` (422) από το `services/errors.py`.
- **Κοινά βήματα** (`services/common.py`): έλεγχος μοναδικότητας, insert/update με audit, activate/deactivate, έλεγχος σεναρίου, ανοχή αθροίσματος 100%.
- **Απάντηση**: πάντα ο φάκελος `{status_code, success, message, data}`. Οι λίστες έχουν `data = {items, total, page, page_size}`.

## Δικαιώματα

| Ενέργεια | Ποιος |
|---|---|
| `GET` | κάθε συνδεδεμένος χρήστης |
| Εγγραφή | `ADMIN`, ή `EXPERT` με `Can_Edit` στο module της οντότητας |
| Εγγραφή από `USER` | ποτέ (403), ακόμα και με `Can_Edit` |

Το `USER` δεν βλέπει ποτέ `Employee_Name` (επιστρέφεται `null`) και η αναζήτησή του δεν ψάχνει σε ονόματα.

## Endpoints

Κάθε master έχει το ίδιο σετ: `GET` λίστα, `GET /{id}`, `POST`, `PATCH /{id}`, `POST /{id}/deactivate`, `POST /{id}/activate`. Δεν υπάρχει `DELETE`. Όλες οι λίστες δέχονται `page`, `page_size` (1–200, default 50) και `is_active` (default `true`).

| Οντότητα | Path | Module | Φίλτρα λίστας | Επιπλέον endpoints |
|---|---|---|---|---|
| Items | `/api/items` | ITEMS | `q`, `prefix`, `group_code`, `bssg_code`, `customer_id`, `is_produced`, `is_purchased` | `PUT /{id}/logistics-units` |
| Customers | `/api/customers` | ITEMS | `q`, `is_internal` | |
| Buildings | `/api/buildings` | BUILDINGS | `q`, `cc_id` | |
| Machines | `/api/machines` | MACHINES | `q`, `category`, `cc_id`, `building_id` | |
| LaborResources | `/api/labor` | LABOR | `q`, `labor_category`, `cc_id` | |
| Resources | `/api/resources` | COST_STRUCTURE | `q`, `resource_type`, `cc_id` | `GET`/`PUT /{id}/activities?scenario_id=`, `GET /allocation-check?scenario_id=` |
| Moulds | `/api/moulds` | MOULDS | `q`, `mould_owner`, `mould_type`, `customer_id` | |
| MouldRuns | `/api/mould-runs` | MOULDS | `q`, `item_id`, `mould_id`, `machine_category` | `PUT /{id}` αντί για `PATCH` (run + outputs + materials μαζί) |
| AssemblyOps | `/api/assembly-ops` | MOULDS | `q`, `item_id`, `operation_type` | |

Οι τιμές και οι όγκοι δεν έχουν `Is_Active`, άρα ούτε activate/deactivate:

| Οντότητα | Path | Module | Endpoints |
|---|---|---|---|
| Prices | `/api/prices` | PRICES | `GET` (φίλτρα `item_id`, `scenario_id`, `on`), `GET /current?item_id=&scenario_id=&on=`, `GET /{id}`, `POST`, `PATCH /{id}` |
| SalesPrices | `/api/sales-prices` | PRICES | όπως οι Prices, με επιπλέον `customer_id` |
| ItemVolumes | `/api/item-volumes` | PRICES | `GET ?scenario_id=` (φίλτρο `item_id`), `PUT ?scenario_id=` (upsert ανά είδος) |

Νέα lookups μόνο για ανάγνωση, για να έχει το UI τα ID που ζητούν τα masters:

| Path | Φίλτρα |
|---|---|
| `GET /api/lookups/cost-centers` | `active_only` |
| `GET /api/lookups/activities` | `cc_id`, `active_only` |
| `GET /api/lookups/scenarios` | `open_only` |

## Επιχειρησιακοί κανόνες

Όλοι οι κωδικοί είναι μοναδικοί (409). Κάθε foreign key ελέγχεται πριν την εγγραφή και δίνει 422 με καθαρό μήνυμα.

**Items**
- Το `Item_Category_Prefix` υπάρχει στο `tbl_ItemCodeRules`, ο κωδικός ξεκινά με αυτό, και είναι το μακρύτερο prefix που ταιριάζει (`12699…` δεν περνά ως `12`).
- BSSG, πυλώνας και ομάδα είναι συνεπή μεταξύ τους, με βάση τα FK των lookups.
- Το `Fason_Base_Item_ID` δεν δείχνει στο ίδιο το είδος.
- Logistics units: `LU_Level` 1–3 και μοναδικό ανά είδος, `Base_Units_Per_LU` > 0.
- Το `PATCH` ελέγχει ολόκληρο το είδος όπως θα είναι μετά την αλλαγή. Το `Is_Active` αλλάζει μόνο με activate/deactivate.

**Buildings**
- Μοναδικό είναι το ζεύγος `Building_Code` + `Zone_Name`.
- `Ownership`: `ΙΔΙΟΚΤΗΤΟ` ή `ΜΙΣΘΩΜΕΝΟ`. `Cost_Basis`: `m2` ή `m3`. `Utilization_Pct` 0–1.
- Το `Resource_ID`, αν δοθεί, είναι πόρος τύπου `BUILDING`.

**Machines**
- `Hours_Per_Day` > 0 και ≤ 24, `Days_Per_Year` 1–366, `Downtime_Pct` 0–1.
- `Residual_Value_EUR` ≤ `Acquisition_Cost_EUR`.
- Το `Resource_ID`, αν δοθεί, είναι πόρος τύπου `MACHINE`.

**LaborResources**
- `Annual_Cost_EUR` ≥ 0 και `Utilization_Rate` 0–1,2 (όπως τα CHECK της βάσης).
- Το `Resource_ID`, αν δοθεί, είναι πόρος τύπου `LABOR`.

**Resources και ποσοστά**
- Ο τύπος ενός πόρου δεν αλλάζει όσο μηχανή, κτίριο ή εργαζόμενος δείχνει σε αυτόν.
- Τα `Share_Pct` ενός πόρου σε ένα σενάριο αθροίζουν 1 ± 0,000001. Κάθε ποσοστό > 0 και ≤ 1, χωρίς διπλή δραστηριότητα, και η δραστηριότητα είναι ενεργή.
- Το `PUT` αντικαθιστά όλη τη λίστα. Άδεια λίστα σβήνει την κατανομή.
- Το σενάριο υπάρχει (404) και δεν είναι κλειδωμένο (422). Η ανάγνωση σε κλειδωμένο επιτρέπεται.
- Το `allocation-check` επιστρέφει τους ενεργούς πόρους χωρίς ποσοστά ή με άθροισμα ≠ 100%. Άδεια λίστα σημαίνει ότι όλα είναι εντάξει.

**Moulds**
- `Mould_Owner = CUSTOMER` θέλει `Customer_ID`.
- `SINGLE`: 1 κοιλότητα. `MULTI_CAVITY` και `FAMILY`: τουλάχιστον 2.
- `QC_Factor` 1–3. `Residual_Value_EUR` ≤ `Acquisition_Cost_EUR`.
- `Current_Cycles` > `Life_Cycles` δεν μπλοκάρει: γεμίζει το πεδίο `warnings` του `Out`.
- Το `Item_ID`, αν δοθεί, είναι είδος τύπου `MOULD` (prefix `9801` ή `9901`).

**MouldRuns**
- Μοναδικά: ο `MouldRun_Code` και το ζεύγος καλούπι + κατηγορία μηχανής.
- Τουλάχιστον ένα output και ένα υλικό.
- Outputs: `SINGLE` βγάζει ένα είδος με 1 τεμάχιο· `MULTI_CAVITY` ένα είδος· σε κάθε τύπο τα τεμάχια ανά κύκλο δεν ξεπερνούν τις κοιλότητες.
- `Cost_Share_Pct`: όλα κενά (μοίρασμα κατά βάρος) ή όλα συμπληρωμένα με άθροισμα 1 ± 0,000001.
- Υλικά: `Mix_Pct` με άθροισμα 1 ± 0,00001. Το είδος είναι αγοραζόμενο ή τύπου `RAW_MAT` / `AUXILIARY`.
- `Operator_Load_Factor` μόνο από το `enums.OPERATOR_LOADS`. `Scrap_Pct` 0–1. `Cycles_Per_Hour` > 0.

**AssemblyOps**
- `Units_Per_Hour` > 0, `Workers_Per_Cell` > 0, `Operation_Type` από το `ASSEMBLY_TYPES`.

**Prices, SalesPrices, ItemVolumes**
- Νέα τιμή σημαίνει νέα γραμμή. Το `PATCH` δέχεται μόνο `Reason`, `Supplier` (μόνο στις αγορές) και `Valid_To`· οτιδήποτε άλλο δίνει 422.
- Η ανοιχτή τιμή που ξεκίνησε νωρίτερα κλείνει αυτόματα την προηγούμενη μέρα από τη νέα.
- Για το ίδιο είδος και σενάριο (και πελάτη, στις πωλήσεις) τα διαστήματα δεν επικαλύπτονται.
- Ξένο νόμισμα: `FX_Rate` και `Price_Local` υποχρεωτικά, και `Price_EUR = Price_Local / FX_Rate` με ανοχή 0,1%. Αν λείπει το `Price_EUR`, υπολογίζεται.
- Τιμή πώλησης σε ισχύ: του πελάτη, αλλιώς η γενική (χωρίς πελάτη).
- Καμία εγγραφή σε κλειδωμένο σενάριο.

## Audit

Κάθε εγγραφή γράφει στο `tbl_AuditLog` μόνο τα πεδία που άλλαξαν, ως `{"Πεδίο": [παλιό, νέο]}`.

| Αλλαγή | `Table_Name` | `Record_Key` |
|---|---|---|
| Master | ο πίνακάς του | `<PK>=<id>` |
| Logistics units | `tbl_LogisticsUnits` | `Item_ID=<id>`, πεδία `LU1`…`LU3` |
| Ποσοστά πόρου | `tbl_ResourceActivities` | `Resource_ID=<id>;Scenario_ID=<id>`, ένα πεδίο ανά `Activity_ID` |
| MouldRun | `tbl_MouldRuns` | `MouldRun_ID=<id>`, με `outputs` και `materials` μέσα |
| Όγκοι | `tbl_ItemVolumes` | `Scenario_ID=<id>`, ένα πεδίο ανά `Item_ID` |

## Ανοιχτά σημεία

- **Λάθος τιμή δεν διορθώνεται.** Δεν υπάρχει `DELETE` ούτε αλλαγή του `Price_EUR`. Μια τιμή με λάθος ποσό μένει στο ιστορικό· ο μόνος τρόπος είναι να κλείσει με `Valid_To` και να μπει νέα από την επόμενη μέρα.
- **Γραφή αριθμών.** Το `POST`/`PUT` επιστρέφει τους αριθμούς όπως στάλθηκαν (`0.041`), το `GET` όπως τους κρατά η βάση (`0.0410`).
- **Δεν υπάρχει τρόπος να δεις ενεργά και ανενεργά μαζί** σε μία κλήση λίστας.
- **Το seed γράφει κατανομές στο κλειδωμένο «Budget 2025»** (`ALLOCATION_SCENARIO`), ενώ το API δεν το επιτρέπει. Οι λίστες `RESOURCES` και `RESOURCE_ACTIVITY` του seed είναι άδειες.
- **Τα lookups λένε το φίλτρο `active_only`, τα masters `is_active`.**
- **Το `allocation-check` δεν έχει σελιδοποίηση.**

## Ερωτήματα για τη Lamaplast

1. **FX:** το `FX_Rate` είναι «ξένο νόμισμα ανά 1 EUR» (`Price_EUR = Price_Local / FX_Rate`). Έτσι το κρατά και το SoftOne; Είναι αποδεκτή η ανοχή 0,1%;
2. **Δικαιώματα:** ο `USER` δεν γράφει πουθενά και ο `EXPERT` μόνο στα modules που του έχουν δοθεί. Αυτό θέλουν;
3. **Ονόματα εργαζομένων:** ο `USER` δεν τα βλέπει πουθενά. Ο `EXPERT` τα βλέπει όλα, ακόμα και χωρίς δικαίωμα στο module `LABOR`. Σωστό;
4. **Υπερωρίες:** `Utilization_Rate` έως 1,2. Είναι το πραγματικό ανώτατο όριο;
5. **Ιδιοκτησία κτιρίου:** αρκούν οι τιμές `ΙΔΙΟΚΤΗΤΟ` και `ΜΙΣΘΩΜΕΝΟ`; (π.χ. leasing;)
6. **Family mould:** χωρίς `Cost_Share_Pct` το κόστος μοιράζεται κατά βάρος. Είναι ο επιθυμητός κανόνας;
7. **MULTI_CAVITY:** βγάζει πάντα ένα μόνο είδος; Ένα καλούπι με δύο διαφορετικά είδη δηλώνεται πάντα `FAMILY`;
8. **Ένα run ανά καλούπι και κατηγορία μηχανής:** αρκεί, ή το ίδιο καλούπι τρέχει με διαφορετικές ρυθμίσεις στην ίδια κατηγορία;
9. **Υλικά του run:** δεκτά είναι τα αγοραζόμενα είδη και τα prefixes `10`–`13`. Μπαίνει ποτέ ημιέτοιμο (`33`) ως υλικό;
10. **Τιμή πώλησης:** όταν ο πελάτης δεν έχει δική του τιμή, ισχύει η γενική. Σωστό;
11. **Κλειδωμένο σενάριο:** ισχύει και για τιμές και όγκους, όχι μόνο για τα ποσοστά πόρων;
12. **Άδεια κατανομή:** επιτρέπεται να μείνει ενεργός πόρος χωρίς ποσοστά μέχρι να τρέξει ο engine;
13. **Διόρθωση λάθους τιμής:** χρειάζονται δικαίωμα διαγραφής ή διόρθωσης για τον `ADMIN`;

## Προτεινόμενες αλλαγές στο σχήμα

Καμία δεν έχει εφαρμοστεί.

| Πίνακας | Αλλαγή | Γιατί |
|---|---|---|
| `tbl_Buildings` | `OWNERSHIPS` και `COST_BASES` στο `enums.py`, και CHECK στο `Ownership` | Σήμερα οι τιμές ορίζονται στο `schemas/buildings.py` και η βάση δέχεται οτιδήποτε |
| `tbl_Machines` | CHECK `Residual_Value_EUR <= Acquisition_Cost_EUR` | Υπάρχει στα καλούπια, λείπει στις μηχανές |
| `tbl_LogisticsUnits` | CHECK `Base_Units_Per_LU > 0` | Το ελέγχει μόνο το API |
| `tbl_Moulds` | CHECK «`CUSTOMER` ⇒ `Customer_ID` όχι κενό» και «`SINGLE` ⇒ `Cavities = 1`» | Το ελέγχει μόνο το API |
| `tbl_Moulds` | Μεγαλύτερο `Wear_Pct` (σήμερα `Numeric(7,4)`) | Ξεχειλίζει αν οι κύκλοι ξεπεράσουν 1000 φορές τη ζωή του καλουπιού |
| `tbl_Prices` | Σχόλιο ή όνομα που δείχνει τη φορά του `FX_Rate` | Δεν φαίνεται από το σχήμα |
| `tbl_SalesPrices` | `Currency`, `FX_Rate`, `Price_Local` | Οι πωλήσεις σε ξένο νόμισμα δεν χωρούν σήμερα |
| `tbl_Prices`, `tbl_SalesPrices` | `Is_Active` ή `Is_Void` | Για να ακυρώνεται μια λάθος τιμή χωρίς διαγραφή |
| `tbl_ResourceActivities` | Σχέση προς `Activity` στο model | Για να επιστρέφονται κωδικός και όνομα δραστηριότητας μαζί με το ποσοστό |
| `tbl_LaborResources` | Απόφαση για το `Annual_Cost_EUR = 0` | Το CHECK το δέχεται, αλλά δίνει ωριαίο κόστος 0 |

## Commits

Τα Items, τα 3.1–3.4 και τα 3.5–3.7 έχουν ήδη γίνει commit. Απομένουν:

```
feat: add assembly ops CRUD
feat: add prices, sales prices and item volumes with validity history
feat: add cost centers, activities and scenarios lookups
chore: add ruff config and sort imports
docs: add phase D summary
```
